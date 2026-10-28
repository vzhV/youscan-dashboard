import type { components } from "./schema";

type Schemas = components["schemas"];

export type Widget = Schemas["WidgetRead"];
export type WidgetType = Schemas["WidgetType"];
export type WidgetSource = Schemas["WidgetSource"];
export type ChartData = Schemas["ChartData"];
export type Dataset = Schemas["DatasetRead"];
export type ImportPreview = Schemas["ImportPreview"];
export type SheetPreview = Schemas["SheetPreview"];
export type ImportSelection = Schemas["ImportSelection"];
export type ImportResult = Schemas["ImportResult"];
export type ErrorBody = Schemas["ErrorBody"];
export type ChartType = Schemas["ChartType"];
export type ColumnKind = Schemas["ColumnKind"];
