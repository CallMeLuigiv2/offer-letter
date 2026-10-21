import type { Lang } from '../model';
import type { LangPack } from './common';
import { python } from './python';
import { rust } from './rust';

export type { LangPack } from './common';
export { python, rust };

export function langPack(lang: Lang): LangPack {
  return lang === 'rust' ? rust : python;
}
