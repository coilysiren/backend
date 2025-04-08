import * as gcp from "@pulumi/gcp";
import * as pulumi from "@pulumi/pulumi";
import * as simpleGit from "simple-git";

export default async (account: gcp.serviceaccount.Account) => {
  let config = new pulumi.Config();

  // Get repository name
  const git = simpleGit.default();
  const remote = (await git.getConfig("remote.origin.url")).value || "";
  const name = remote.split(":")[1].split(".")[0];
  const nameDashed = name.replace("/", "-");

  // Create Redis instance
  const redis = new gcp.redis.Instance(nameDashed, {
    name: nameDashed,
    tier: "BASIC",
    memorySizeGb: 1,
  });

  // Allow the service account to manage the Redis instance
  new gcp.projects.IAMMember(`${nameDashed}-redis-editor`, {
    project: account.project,
    role: "roles/redis.editor",
    member: pulumi.interpolate`serviceAccount:${account.email}`,
  });

  // Allow the service account to manage the Redis instance
  new gcp.projects.IAMMember(`${nameDashed}-redis-viewer`, {
    project: account.project,
    role: "roles/redis.viewer",
    member: pulumi.interpolate`serviceAccount:${account.email}`,
  });

  // Redis connection info
  // Note: Redis on GCP doesn't use passwords - it uses IAM authentication
  // The host will be available at redis.host
  // The port will be available at redis.port (default 6379)
  // Example connection string: redis://<host>:6379

  return { redis };
};
