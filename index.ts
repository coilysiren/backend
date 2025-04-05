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
  const name = remote.split(":")[1].split(".")[0].replace("/", "-");

  // Get current user's email
  const auth = new GoogleAuth();
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  const oAuth2Client = new OAuth2Client();
  const tokenInfo = await oAuth2Client.getTokenInfo(token.token as string);
  const email = tokenInfo.email;

  // Create GCP Artifact Registry Repository
  const repo = new gcp.artifactregistry.Repository(name, {
    format: "docker",
    repositoryId: name,
  });

  // Create a serice account for pushing our docker images
  const account = new gcp.serviceaccount.Account(name, {
    accountId: name,
    displayName: `Allows pushing docker images to ${name}`,
  });

  // Allow the service account to push our docker images
  new gcp.artifactregistry.RepositoryIamBinding(name, {
    project: repo.project,
    location: repo.location,
    repository: repo.name,
    role: "roles/artifactregistry.writer",
    members: [pulumi.interpolate`serviceAccount:${account.email}`],
  });

  // Allow people to act as the service account
  new gcp.serviceaccount.IAMMember(`${name}-faker`, {
    serviceAccountId: pulumi.interpolate`${account.id}`,
    role: "roles/iam.serviceAccountTokenCreator",
    member: `user:${email}`,
  });

  // Create a global static IP address for this service's ingress
  const ip = new gcp.compute.GlobalAddress(name, {
    name: name,
    addressType: "EXTERNAL",
  });

  // Get existing AWS route53 hosted zone
  const hostedZone = aws.route53.getZone({
    name: config.require("DNS_ZONE"),
  });

  // Create a CNAME record pointing the zone to the static IP address
  new aws.route53.Record(name, {
    zoneId: hostedZone.then((zone) => zone.id),
    name: config.require("DNS_NAME"),
    type: "A",
    ttl: 60,
    records: [ip.address],
  });

  return { repo, account, ip };
};
