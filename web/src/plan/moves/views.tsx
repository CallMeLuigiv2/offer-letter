// One switch from a move to its panel, shared by the page and the worked-plan replay.
import type { MoveId } from '../engine';
import { BridgeMove } from './Bridge';
import { ContractsMove } from './Contracts';
import { DecideMove } from './Decide';
import { ExamplesMove } from './Examples';
import { PiecesMove } from './Pieces';
import { ReadMove } from './Read';
import { RestateMove } from './Restate';
import { ReviewMove } from './Review';
import { RunMove } from './Run';

export function MoveView({ move }: { move: MoveId }) {
  switch (move) {
    case 'read':
      return <ReadMove />;
    case 'restate':
      return <RestateMove />;
    case 'bridge':
      return <BridgeMove />;
    case 'examples':
      return <ExamplesMove />;
    case 'pieces':
      return <PiecesMove />;
    case 'contracts':
      return <ContractsMove />;
    case 'run':
      return <RunMove />;
    case 'decide':
      return <DecideMove />;
    case 'review':
      return <ReviewMove />;
    default:
      return null;
  }
}
