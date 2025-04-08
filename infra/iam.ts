import * as gcp from "@pulumi/gcp";
import * as pulumi from "@pulumi/pulumi";
import * as simpleGit from "simple-git";
import { GoogleAuth, OAuth2Client } from "google-auth-library";

export default async () => {
  // Get repository name
  const git = simpleGit.default();
  const remote = (await git.getConfig("remote.origin.url")).value || "";
  const name = remote.split(":")[1].split(".")[0];
  const nameDashed = name.replace("/", "-");

  // Get current user's email
  const auth = new GoogleAuth();
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  const oAuth2Client = new OAuth2Client();
  const tokenInfo = await oAuth2Client.getTokenInfo(token.token as string);
  const email = tokenInfo.email;

  // Get project number
  const project = gcp.organizations.getProject({});
  const projectNumber = project.then((p) => p.number);

  // Create a workload identity pool
  const pool = new gcp.iam.WorkloadIdentityPool(nameDashed, {
    workloadIdentityPoolId: nameDashed,
    description: `Workload identity pool for ${nameDashed}`,
  });

  // Create a workload identity provider
  new gcp.iam.WorkloadIdentityPoolProvider(nameDashed, {
    displayName: nameDashed,
    description: `Workload identity provider for ${nameDashed}`,
    workloadIdentityPoolId: pool.workloadIdentityPoolId,
    workloadIdentityPoolProviderId: nameDashed,
    oidc: {
      issuerUri: "https://token.actions.githubusercontent.com",
    },
    attributeMapping: {
      "google.subject": "assertion.sub",
      "attribute.actor": "assertion.actor",
      "attribute.repository": "assertion.repository",
    },
    attributeCondition: `attribute.repository == "${name}"`,
  });

  // Create a service account for deploying the service
  const account = new gcp.serviceaccount.Account(nameDashed, {
    accountId: nameDashed,
    displayName: `Allows deploying the ${name} service`,
  });

  // Allow various actors to generate access tokens for the service account: Github Actions
  new gcp.serviceaccount.IAMMember(`${nameDashed}-token-creator-github`, {
    serviceAccountId: pulumi.interpolate`${account.id}`,
    role: "roles/iam.serviceAccountTokenCreator",
    member: pulumi.interpolate`principalSet://iam.googleapis.com/projects/${projectNumber}/locations/global/workloadIdentityPools/${nameDashed}/attribute.repository/${name}`,
  });

  // Allow various actors to generate access tokens for the service account: service account itself
  new gcp.serviceaccount.IAMMember(`${nameDashed}-token-creator-itself`, {
    serviceAccountId: pulumi.interpolate`${account.id}`,
    role: "roles/iam.serviceAccountTokenCreator",
    member: pulumi.interpolate`serviceAccount:${account.email}`, // The service account itself
  });

  // Allow various actors to generate access tokens for the service account: humans
  new gcp.serviceaccount.IAMMember(`${nameDashed}-token-creator-humans`, {
    serviceAccountId: pulumi.interpolate`${account.id}`,
    role: "roles/iam.serviceAccountTokenCreator",
    member: `user:${email}`,
  });

  // Allow the service account to read the state bucket
  new gcp.storage.BucketIAMBinding(`${nameDashed}-state-bucket-reader`, {
    bucket: "coilysiren-deploy-pulumi-state",
    role: "roles/storage.objectViewer",
    members: [pulumi.interpolate`serviceAccount:${account.email}`],
  });

  return { account };
};
