import dns from "./infra/dns";
import repository from "./infra/repository";
import iam from "./infra/iam";

export = async () => {
  const { account } = await iam();
  const { ip } = await dns();
  const { repo } = await repository(account);

  return { repo, ip };
};
