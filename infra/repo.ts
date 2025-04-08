import * as gcp from "@pulumi/gcp";
import * as pulumi from "@pulumi/pulumi";
import * as simpleGit from "simple-git";

export default async (account: gcp.serviceaccount.Account) => {
  // Get repository name
  const git = simpleGit.default();
  const remote = (await git.getConfig("remote.origin.url")).value || "";
  const name = remote.split(":")[1].split(".")[0];
  const nameDashed = name.replace("/", "-");

  // Create GCP Artifact Registry Repository
  const repo = new gcp.artifactregistry.Repository(nameDashed, {
    format: "docker",
    repositoryId: nameDashed,
  });

  // Allow the service account to read the artifact registry
  new gcp.artifactregistry.RepositoryIamMember(`${nameDashed}-reader`, {
    member: pulumi.interpolate`serviceAccount:${account.email}`,
    role: "roles/artifactregistry.reader",
    project: account.project,
    location: repo.location,
    repository: repo.name,
  });

  // Allow the service account to push our docker images
  new gcp.artifactregistry.RepositoryIamMember(`${nameDashed}-writer`, {
    member: pulumi.interpolate`serviceAccount:${account.email}`,
    role: "roles/artifactregistry.writer",
    project: account.project,
    location: repo.location,
    repository: repo.name,
  });

  return { repo };
};
