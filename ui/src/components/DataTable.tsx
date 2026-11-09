import {
  type ColumnDef, type SortingState, flexRender, getCoreRowModel, getFilteredRowModel, getSortedRowModel, useReactTable,
} from "@tanstack/react-table";
import { type ReactNode, useState } from "react";

interface Props<T> {
  data: T[];
  columns: ColumnDef<T, any>[];
  globalFilter?: string;
  initialSort?: SortingState;
  onRowClick?: (row: T) => void;
  rowLabel?: (row: T) => string;
  empty?: ReactNode;
}

export function DataTable<T>({ data, columns, globalFilter, initialSort = [], onRowClick, rowLabel, empty }: Props<T>) {
  const [sorting, setSorting] = useState<SortingState>(initialSort);
  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: "includesString",
  });
  const rows = table.getRowModel().rows;

  return (
    <div className="table-wrap">
      <table className="grid">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => {
                const sorted = h.column.getIsSorted();
                return (
                  <th key={h.id} style={{ width: h.column.columnDef.size ? h.column.getSize() : undefined }}
                      aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}>
                    {h.isPlaceholder ? null : h.column.getCanSort() ? (
                      <button onClick={h.column.getToggleSortingHandler()}>
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        <span className="sort" aria-hidden="true">{sorted === "asc" ? "▲" : sorted === "desc" ? "▼" : ""}</span>
                      </button>
                    ) : flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}
                tabIndex={onRowClick ? 0 : undefined}
                aria-label={rowLabel?.(row.original)}
                onClick={() => onRowClick?.(row.original)}
                onKeyDown={(e) => { if (e.key === "Enter") onRowClick?.(row.original); }}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (empty ?? <div className="empty">No matching rows.</div>)}
    </div>
  );
}
