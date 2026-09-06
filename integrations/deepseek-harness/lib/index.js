import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';

export const name = 'archipam-dsh';
export const PACKAGE_NAME = '@licpmb/archipam-dsh';

export function resolveArchiPamSkillRoot(profileBaseUrl) {
  if (!profileBaseUrl) {
    throw new Error('archipam-dsh: missing DSH profile baseUrl for package resolution');
  }
  let manifestPath;
  try {
    manifestPath = createRequire(profileBaseUrl).resolve(`${PACKAGE_NAME}/package.json`);
  } catch (error) {
    throw new Error(
      `archipam-dsh: cannot resolve ${PACKAGE_NAME}/package.json from the DSH profile`,
      { cause: error },
    );
  }
  return join(dirname(manifestPath), 'skills');
}
