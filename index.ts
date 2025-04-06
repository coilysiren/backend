import * as gcp from "@pulumi/gcp";
import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import * as simpleGit from "simple-git";
import { GoogleAuth, OAuth2Client } from "google-auth-library";

export = async () => {
  let config = new pulumi.Config();

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

  // Create a workload identity pool
  const pool = new gcp.iam.WorkloadIdentityPool(nameDashed, {
    workloadIdentityPoolId: nameDashed,
    description: `Workload identity pool for ${nameDashed}`,
  });

  // Create a workload identity provider
  const identityProvider = new gcp.iam.WorkloadIdentityPoolProvider(
    nameDashed,
    {
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
      attributeCondition: `attribute.repository == ${name}`,
    }
  );

  // Create GCP Artifact Registry Repository
  const repo = new gcp.artifactregistry.Repository(nameDashed, {
    format: "docker",
    repositoryId: nameDashed,
  });
  // Create a serice account for pushing our docker images
  const account = new gcp.serviceaccount.Account(nameDashed, {
    accountId: nameDashed,
    displayName: `Allows deploying the ${name} service`,
  });

  // Allow the service account to push our docker images
  new gcp.artifactregistry.RepositoryIamBinding(nameDashed, {
    project: repo.project,
    location: repo.location,
    repository: repo.name,
    role: "roles/artifactregistry.writer",
    members: [pulumi.interpolate`serviceAccount:${account.email}`],
  });

  // Allow humans to act as the service account
  new gcp.serviceaccount.IAMBinding(`${nameDashed}-token-creator-humans`, {
    serviceAccountId: pulumi.interpolate`${account.id}`,
    role: "roles/iam.serviceAccountTokenCreator",
    members: [`user:${email}`],
  });

  new gcp.serviceaccount.IAMBinding(`${nameDashed}-github-actions`, {
    serviceAccountId: pulumi.interpolate`${account.id}`,
    role: "roles/iam.workloadIdentityUser",
    members: [
      pulumi.interpolate`principalSet://iam.googleapis.com/${pool.name}/attribute.repository/${name}`,
    ],
  });

  // Create a global static IP address for this service's ingress
  const ip = new gcp.compute.GlobalAddress(nameDashed, {
    name: nameDashed,
    addressType: "EXTERNAL",
  });

  // Get existing AWS route53 hosted zone
  const hostedZone = aws.route53.getZone({
    name: config.require("dns-zone"),
  });

  // Create a CNAME record pointing the zone to the static IP address
  new aws.route53.Record(nameDashed, {
    zoneId: hostedZone.then((zone: aws.route53.GetZoneResult) => zone.id),
    name: config.require("dns-name"),
    type: "A",
    ttl: 60,
    records: [ip.address],
  });

  return { repo, account, ip, identityProvider };
};
