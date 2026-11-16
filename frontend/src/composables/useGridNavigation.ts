import { ref } from "vue";

export interface GridCellInterface {
  row: number;
  column: number;
}

export function nextGridCell(cell: GridCellInterface, key: string, rowCount: number, columnCount: number): GridCellInterface | null {
  const lastRow = rowCount - 1;
  const lastColumn = columnCount - 1;

  switch (key) {
    case "ArrowLeft":
      return cell.column > 0 ? { ...cell, column: cell.column - 1 } : null;
    case "ArrowRight":
      return cell.column < lastColumn ? { ...cell, column: cell.column + 1 } : null;
    case "ArrowUp":
      return cell.row > 0 ? { ...cell, row: cell.row - 1 } : null;
    case "ArrowDown":
      return cell.row < lastRow ? { ...cell, row: cell.row + 1 } : null;
    case "Home":
      return { ...cell, column: 0 };
    case "End":
      return { ...cell, column: lastColumn };
    default:
      return null;
  }
}

export function useGridNavigation(size: () => { rowCount: number; columnCount: number }) {
  const activeCell = ref<GridCellInterface>({ row: 0, column: 0 });

  function tabIndex(row: number, column: number) {
    return activeCell.value.row === row && activeCell.value.column === column ? 0 : -1;
  }

  function cellPosition(target: EventTarget | null): GridCellInterface | null {
    const cell = target instanceof HTMLElement ? target.closest<HTMLElement>("[data-row][data-column]") : null;

    return cell ? { row: Number(cell.dataset.row), column: Number(cell.dataset.column) } : null;
  }

  function onFocusIn(event: FocusEvent) {
    const position = cellPosition(event.target);

    if (position) {
      activeCell.value = position;
    }
  }

  function onKeyDown(event: KeyboardEvent) {
    const position = cellPosition(event.target);

    if (!position) {
      return;
    }

    const { rowCount, columnCount } = size();
    const next = nextGridCell(position, event.key, rowCount, columnCount);

    if (!next) {
      return;
    }

    event.preventDefault();
    activeCell.value = next;
    (event.currentTarget as HTMLElement).querySelector<HTMLElement>(`[data-row="${next.row}"][data-column="${next.column}"]`)?.focus();
  }

  return { activeCell, tabIndex, onFocusIn, onKeyDown };
}
