/**
 * Walkability for the office: built from tile properties (collides / seat)
 * and searched with easystar.js (4-way A*, synchronous; the map is tiny).
 */
import * as EasyStar from 'easystarjs';

export const FREE = 0;
export const BLOCKED = 1;
export const SEAT = 2;
/** Paths may cross a chair, but only when there is no other way. */
const SEAT_COST = 12;

export interface TilePoint {
  x: number;
  y: number;
}

export class WalkGrid {
  readonly width: number;
  readonly height: number;
  readonly cells: number[][];
  private finder: EasyStar.js;

  constructor(cells: number[][]) {
    this.cells = cells;
    this.height = cells.length;
    this.width = cells[0]?.length ?? 0;
    this.finder = new EasyStar.js();
    this.finder.setGrid(cells);
    this.finder.setAcceptableTiles([FREE, SEAT]);
    this.finder.setTileCost(SEAT, SEAT_COST);
    this.finder.enableSync();
    this.finder.disableDiagonals();
  }

  at(x: number, y: number): number {
    if (x < 0 || y < 0 || x >= this.width || y >= this.height) return BLOCKED;
    return this.cells[y][x];
  }

  walkable(x: number, y: number): boolean {
    return this.at(x, y) !== BLOCKED;
  }

  /** A* from a to b in tile coords; null when unreachable. Includes both ends. */
  path(a: TilePoint, b: TilePoint): TilePoint[] | null {
    if (!this.walkable(b.x, b.y)) return null;
    if (a.x === b.x && a.y === b.y) return [{ x: a.x, y: a.y }];
    let result: TilePoint[] | null = null;
    // easystar only checks the end tile, so a start on a blocked tile still works.
    this.finder.findPath(a.x, a.y, b.x, b.y, (p) => {
      result = p ? p.map((q) => ({ x: q.x, y: q.y })) : null;
    });
    this.finder.calculate();
    return result;
  }
}
