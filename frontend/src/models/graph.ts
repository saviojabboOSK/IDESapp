export interface GraphConfig {
  id: string;
  title: string;
  chart_type: string;
  metrics: string[];
  time_range: string;
  settings: {
    color_scheme: string[];
    show_legend: boolean;
    show_grid: boolean;
    animate?: boolean;
    smooth_lines?: boolean;
    fill_area?: boolean;
    show_points?: boolean;
    y_axis_min?: number;
    y_axis_max?: number;
  };
  layout: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  is_ai_generated?: boolean;
  auto_refresh?: boolean;
  refresh_interval?: number;
}
