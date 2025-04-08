import dns from "./infra/dns";
import repo from "./infra/repo";
import iam from "./infra/iam";
import redis from "./infra/redis";

export = async () => {
  const { account } = await iam();
  const { ip } = await dns();
  const { repo: _repo } = await repo(account);
  const { redis: _redis } = await redis(account);

  return { repo: _repo, ip, redis: _redis };
};
