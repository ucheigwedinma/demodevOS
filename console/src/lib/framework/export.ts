/**
 * Client-side export utilities for resource tables.
 * Supports CSV, XLSX (Excel), and PDF formats.
 */

import type { ColumnDef } from "./types";

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function formatCellValue(value: unknown, type: ColumnDef["type"]): string | number {
  if (value == null) return "";

  switch (type) {
    case "date": {
      try {
        return new Date(value as string).toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        });
      } catch {
        return String(value);
      }
    }
    case "datetime": {
      try {
        return new Date(value as string).toLocaleString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch {
        return String(value);
      }
    }
    case "currency": {
      const n = Number(value);
      return isNaN(n) ? String(value) : n;
    }
    case "number": {
      const n = Number(value);
      return isNaN(n) ? String(value) : n;
    }
    case "boolean":
      return value ? "Yes" : "No";
    default:
      return String(value);
  }
}

function prepareExportData(
  columns: ColumnDef[],
  data: Record<string, unknown>[],
): { headers: string[]; rows: (string | number)[][] } {
  const visible = columns.filter((c) => !c.hidden);
  const headers = visible.map((c) => c.label);
  const rows = data.map((row) =>
    visible.map((col) => formatCellValue(row[col.key], col.type)),
  );
  return { headers, rows };
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function timestamp(): string {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// CSV Export
// ---------------------------------------------------------------------------

export function exportCSV(
  columns: ColumnDef[],
  data: Record<string, unknown>[],
  resourceLabel: string,
): void {
  const { headers, rows } = prepareExportData(columns, data);

  const escape = (v: string | number): string => {
    const s = String(v);
    if (s.includes(",") || s.includes('"') || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const lines = [headers.map(escape).join(",")];
  for (const row of rows) {
    lines.push(row.map(escape).join(","));
  }

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  downloadBlob(blob, `${slugify(resourceLabel)}-${timestamp()}.csv`);
}

// ---------------------------------------------------------------------------
// XLSX Export
// ---------------------------------------------------------------------------

export async function exportXLSX(
  columns: ColumnDef[],
  data: Record<string, unknown>[],
  resourceLabel: string,
): Promise<void> {
  const XLSX = await import("xlsx");
  const { headers, rows } = prepareExportData(columns, data);

  const aoa = [headers, ...rows];
  const ws = XLSX.utils.aoa_to_sheet(aoa);

  // Auto-fit column widths
  const colWidths = headers.map((h, i) => {
    let maxLen = h.length;
    for (const row of rows) {
      const cellLen = String(row[i]).length;
      if (cellLen > maxLen) maxLen = cellLen;
    }
    return { wch: Math.min(maxLen + 2, 50) };
  });
  ws["!cols"] = colWidths;

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, resourceLabel.slice(0, 31));
  XLSX.writeFile(wb, `${slugify(resourceLabel)}-${timestamp()}.xlsx`);
}

// ---------------------------------------------------------------------------
// PDF Export
// ---------------------------------------------------------------------------

export async function exportPDF(
  columns: ColumnDef[],
  data: Record<string, unknown>[],
  resourceLabel: string,
): Promise<void> {
  const { default: jsPDF } = await import("jspdf");
  const autoTable = (await import("jspdf-autotable")).default;

  const { headers, rows } = prepareExportData(columns, data);

  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });

  // Title
  doc.setFontSize(14);
  doc.setTextColor(23, 23, 23);
  doc.text(resourceLabel, 14, 15);

  // Subtitle (date)
  doc.setFontSize(9);
  doc.setTextColor(115, 115, 115);
  doc.text(`Exported ${new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`, 14, 21);

  // Table
  autoTable(doc, {
    startY: 26,
    head: [headers],
    body: rows.map((r) => r.map(String)),
    styles: {
      fontSize: 8,
      cellPadding: 3,
      textColor: [23, 23, 23],
      lineColor: [229, 229, 229],
      lineWidth: 0.1,
    },
    headStyles: {
      fillColor: [245, 245, 245],
      textColor: [64, 64, 64],
      fontStyle: "bold",
      lineColor: [229, 229, 229],
    },
    alternateRowStyles: {
      fillColor: [250, 250, 250],
    },
    margin: { left: 14, right: 14 },
    didDrawPage: (hookData: { pageNumber: number }) => {
      // Footer with page number
      const pageCount = doc.getNumberOfPages();
      doc.setFontSize(8);
      doc.setTextColor(150, 150, 150);
      doc.text(
        `Page ${hookData.pageNumber} of ${pageCount}`,
        doc.internal.pageSize.getWidth() - 14,
        doc.internal.pageSize.getHeight() - 8,
        { align: "right" },
      );
    },
  });

  doc.save(`${slugify(resourceLabel)}-${timestamp()}.pdf`);
}

// ---------------------------------------------------------------------------
// Download helper
// ---------------------------------------------------------------------------

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
