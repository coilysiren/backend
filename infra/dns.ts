import * as gcp from "@pulumi/gcp";
import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import * as simpleGit from "simple-git";

export default async () => {
  let config = new pulumi.Config();

  // Get repository name
  const git = simpleGit.default();
  const remote = (await git.getConfig("remote.origin.url")).value || "";
  const name = remote.split(":")[1].split(".")[0];
  const nameDashed = name.replace("/", "-");

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

  return { ip };
};
