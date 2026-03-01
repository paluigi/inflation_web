import flet as ft
import flet_charts as fch
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
from io import BytesIO


class InflationDataExplorer:
    """Flet application for exploring inflation data with an object-oriented design."""
    
    def __init__(self):
        # Initialize state variables
        self.tab1_selected_coicops: list = []
        self.tab1_selected_geo: str | None = None
        self.tab2_selected_coicop: str | None = None
        self.tab2_selected_geos: list = []
        self.selected_unit: str | None = None
        self.from_date: str = ""
        self.to_date: str = ""
        self.current_table: ft.DataTable | None = None
        self.current_data: pd.DataFrame | None = None
        
        # Sidebar state
        self.sidebar_expanded = True
        self.sidebar_width_expanded = 420
        self.sidebar_width_collapsed = 50
        
        # Page reference (set in main)
        self.page: ft.Page | None = None
        
        # Load mapping files
        self.coicop_df = pd.read_csv("src/assets/maps/coicop18.csv")
        self.geo_df = pd.read_csv("src/assets/maps/geo.csv")
        self.unit_df = pd.read_csv("src/assets/maps/unit.csv")
        
        # Create dropdown options
        self.coicop_options = [
            ft.dropdown.Option(code, f"{code} - {name}") 
            for code, name in zip(self.coicop_df['code'], self.coicop_df['name'])
        ]
        self.geo_options = [
            ft.dropdown.Option(code, f"{code} - {name}") 
            for code, name in zip(self.geo_df['code'], self.geo_df['name'])
        ]
        self.unit_options = [
            ft.dropdown.Option(code, f"{name} ({code})") 
            for code, name in zip(self.unit_df['code'], self.unit_df['name'])
        ]
        
        # UI components (initialized in _create_ui_components)
        self.data_display: ft.Column | None = None
        self.tabs: ft.Tabs | None = None
        self.coicop_checkboxes_tab1: list = []
        self.geo_checkboxes_tab2: list = []
        self.geo_dropdown_tab1: ft.Dropdown | None = None
        self.coicop_dropdown_tab2: ft.Dropdown | None = None
        self.unit_dropdown: ft.Dropdown | None = None
        self.from_date_input: ft.TextField | None = None
        self.to_date_input: ft.TextField | None = None
        self.sidebar: ft.Container | None = None
        self.sidebar_content: ft.Column | None = None
        self.toggle_button: ft.IconButton | None = None
        self.last_update_text: ft.Text | None = None
        
        # Theme state
        self.is_dark_mode = False
        self.theme_toggle_button: ft.IconButton | None = None
        self.app_bar: ft.Container | None = None
        self.app_bar_title: ft.Text | None = None
        self.last_update_icon: ft.Icon | None = None
        self.last_update_text: ft.Text | None = None
        
        # Search filter state
        self.tab1_coicop_search_text: str = ""
        self.tab2_geo_search_text: str = ""
        
        # Search filter components
        self.coicop_search_tab1: ft.TextField | None = None
        self.geo_search_tab2: ft.TextField | None = None
        self.coicop_checkbox_container_tab1: ft.Column | None = None
        self.geo_checkbox_container_tab2: ft.Column | None = None
    
    def get_last_update_date(self) -> str:
        """Read the last update date from file."""
        try:
            with open("src/assets/last_update.txt", "r") as f:
                return f.read().strip()
        except Exception:
            return "Unknown"
    
    def toggle_sidebar(self, e):
        """Toggle sidebar expanded/collapsed state."""
        self.sidebar_expanded = not self.sidebar_expanded
        
        if self.sidebar_expanded:
            self.sidebar.width = self.sidebar_width_expanded
            self.toggle_button.icon = ft.Icons.MENU_OPEN
            self.sidebar_content.visible = True
        else:
            self.sidebar.width = self.sidebar_width_collapsed
            self.toggle_button.icon = ft.Icons.MENU
            self.sidebar_content.visible = False
        
        self.page.update()
    
    def toggle_theme(self, e):
        """Toggle between dark and light theme."""
        self.is_dark_mode = not self.is_dark_mode
        
        if self.is_dark_mode:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_toggle_button.icon = ft.Icons.LIGHT_MODE
            self.theme_toggle_button.tooltip = "Switch to light mode"
            # Update app bar colors for dark mode
            self.app_bar.bgcolor = ft.Colors.GREY_900
            self.app_bar.border = ft.Border(bottom=ft.BorderSide(1, ft.Colors.GREY_700))
            self.app_bar_title.color = ft.Colors.WHITE
            self.last_update_icon.color = ft.Colors.GREY_400
            self.last_update_text.color = ft.Colors.GREY_400
            # Update sidebar colors for dark mode
            self.sidebar.bgcolor = ft.Colors.GREY_800
            self.sidebar.border = ft.Border(right=ft.BorderSide(1, ft.Colors.GREY_700))
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_toggle_button.icon = ft.Icons.DARK_MODE
            self.theme_toggle_button.tooltip = "Switch to dark mode"
            # Update app bar colors for light mode
            self.app_bar.bgcolor = ft.Colors.BLUE_50
            self.app_bar.border = ft.Border(bottom=ft.BorderSide(1, ft.Colors.GREY_300))
            self.app_bar_title.color = None  # Use default
            self.last_update_icon.color = ft.Colors.GREY_600
            self.last_update_text.color = ft.Colors.GREY_600
            # Update sidebar colors for light mode
            self.sidebar.bgcolor = ft.Colors.GREY_50
            self.sidebar.border = ft.Border(right=ft.BorderSide(1, ft.Colors.GREY_300))
        
        # Refresh table to update colors
        if self.current_data is not None and not self.current_data.empty:
            self.update_table()
        
        self.page.update()
    
    def load_and_filter_data(self) -> pd.DataFrame:
        """Load and filter data based on current tab and selections.
        
        Returns data in wide format with TIME_PERIOD as rows and 
        geos/COICOPs as columns.
        """
        if not self.selected_unit:
            return pd.DataFrame()
        
        active_tab = self.tabs.selected_index
        
        if active_tab == 0:  # Tab 1: multiple COICOPs, single geo
            if not self.tab1_selected_geo or len(self.tab1_selected_coicops) == 0:
                return pd.DataFrame()
            
            # Load geo file
            file_path = f"src/assets/data/{self.tab1_selected_geo}.csv"
            filter_column = 'coicop18'
            filter_values = self.tab1_selected_coicops
            select_columns = ['coicop18', 'unit', 'TIME_PERIOD', 'value']
            
        else:  # Tab 2: single COICOP, multiple geos
            if not self.tab2_selected_coicop or len(self.tab2_selected_geos) == 0:
                return pd.DataFrame()
            
            # Load COICOP file
            file_path = f"src/assets/data/{self.tab2_selected_coicop}.csv"
            filter_column = 'geo'
            filter_values = self.tab2_selected_geos
            select_columns = ['geo', 'unit', 'TIME_PERIOD', 'value']
        
        # Load file
        if not os.path.exists(file_path):
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
        
        # Apply filters
        filtered_df = df[
            (df[filter_column].isin(filter_values)) &
            (df['unit'] == self.selected_unit)
        ]
        
        # Apply date filter if specified
        if self.from_date:
            filtered_df = filtered_df[filtered_df['TIME_PERIOD'] >= self.from_date]
        if self.to_date:
            filtered_df = filtered_df[filtered_df['TIME_PERIOD'] <= self.to_date]
        
        # Select relevant columns
        result_df = filtered_df[select_columns]
        
        # Pivot to wide format: TIME_PERIOD as rows, filter_column as columns, value as cell values
        if not result_df.empty:
            result_df = result_df.pivot(
                index='TIME_PERIOD',
                columns=filter_column,
                values='value'
            )
            # Sort by TIME_PERIOD descending
            result_df = result_df.sort_index(ascending=False)
            # Reset index to make TIME_PERIOD a column
            result_df = result_df.reset_index()
            
            # Rename columns from codes to names
            if active_tab == 0:  # Tab 1: rename COICOP codes to names
                code_to_name = dict(zip(self.coicop_df['code'], self.coicop_df['name']))
            else:  # Tab 2: rename geo codes to names
                code_to_name = dict(zip(self.geo_df['code'], self.geo_df['name']))
            # Add TIME_PERIOD to the mapping
            code_to_name["TIME_PERIOD"] = "DATE"
            # Rename columns
            result_df = result_df.rename(columns=code_to_name)
        
        self.current_data = result_df
        return result_df
    
    # Color palette for different lines (shared between chart and legend)
    CHART_COLORS = [
        ft.Colors.BLUE,
        ft.Colors.RED,
        ft.Colors.GREEN,
        ft.Colors.PURPLE,
        ft.Colors.ORANGE,
        ft.Colors.TEAL,
        ft.Colors.PINK,
        ft.Colors.INDIGO,
        ft.Colors.AMBER,
        ft.Colors.CYAN,
    ]
    
    def create_legend(self, value_cols: list) -> ft.Row:
        """Create a custom legend for the chart.
        
        Args:
            value_cols: List of column names to display in legend.
        
        Returns:
            A Row widget containing legend items.
        """
        legend_items = []
        for i, col in enumerate(value_cols):
            color = self.CHART_COLORS[i % len(self.CHART_COLORS)]
            display_name = col
            legend_items.append(
                ft.Row(
                    [
                        ft.Container(
                            width=20,
                            height=4,
                            bgcolor=color,
                            border_radius=2,
                        ),
                        ft.Text(display_name, size=12),
                    ],
                    spacing=5,
                )
            )
        return ft.Row(legend_items, spacing=20, wrap=True, alignment=ft.MainAxisAlignment.CENTER)
    
    def create_line_chart(self, data: pd.DataFrame) -> fch.LineChart:
        """Create a line chart from the filtered data.
        
        Args:
            data: DataFrame in wide format with DATE column and value columns.
        
        Returns:
            A LineChart widget with interactive tooltips.
        """
        
        # Get date column and value columns
        date_col = "DATE"
        value_cols = [col for col in data.columns if col != date_col]
        
        # Get dates list (for axis labels and tooltips)
        # Sort dates ascending for the chart (reverse of table display)
        dates = data[date_col].tolist()
        dates_sorted = sorted(dates)
        
        # Create data series (one line per value column)
        data_series = []
        for i, col in enumerate(value_cols):
            color = self.CHART_COLORS[i % len(self.CHART_COLORS)]
            
            # Create points for this series
            points = []
            for idx, date in enumerate(dates_sorted):
                row = data[data[date_col] == date]
                if not row.empty:
                    value = row[col].values[0]
                    if pd.notna(value):
                        points.append(
                            fch.LineChartDataPoint(
                                x=idx,
                                y=value,
                                tooltip=f"{date}: {value:.1f}"
                            )
                        )
            
            if points:
                data_series.append(
                    fch.LineChartData(
                        color=color,
                        stroke_width=3,
                        curved=False,
                        points=points,
                    )
                )
        
        # Calculate min/max for Y axis
        all_values = data[value_cols].values.flatten()
        all_values = all_values[~pd.isna(all_values)]
        min_y = min(all_values) if len(all_values) > 0 else 0
        max_y = max(all_values) if len(all_values) > 0 else 100
        # Add some padding to Y axis
        y_padding = (max_y - min_y) * 0.1 if max_y != min_y else 5
        min_y = min_y - y_padding
        max_y = max_y + y_padding
        
        # Create bottom axis labels (dates)
        # Show a subset of dates to avoid overcrowding
        num_dates = len(dates_sorted)
        if num_dates <= 10:
            # Show all dates
            label_indices = list(range(num_dates))
        else:
            # Show approximately 8 evenly spaced labels
            step = num_dates // 8
            label_indices = list(range(0, num_dates, step))
            if label_indices[-1] != num_dates - 1:
                label_indices.append(num_dates - 1)
        
        bottom_axis_labels = [
            fch.ChartAxisLabel(
                value=idx,
                label=ft.Container(
                    margin=ft.Margin(top=10),
                    content=ft.Text(
                        value=dates_sorted[idx],
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.with_opacity(0.7, ft.Colors.ON_SURFACE),
                    ),
                ),
            )
            for idx in label_indices
        ]
        
        # Create the chart
        chart = fch.LineChart(
            data_series=data_series,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE)),
            tooltip=fch.LineChartTooltip(
                bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.WHITE),
            ),
            interactive=True,
            min_y=min_y,
            max_y=max_y,
            min_x=0,
            # Padding to enable tooltip hovering on the last point
            max_x=(len(dates_sorted) - 1 if len(dates_sorted) > 1 else 1) + 0.1, 
            expand=True,
            height=400,
            horizontal_grid_lines=fch.ChartGridLines(
                interval=(max_y - min_y) / 5,
                color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE),
                width=1,
            ),
            vertical_grid_lines=fch.ChartGridLines(
                interval=1,
                color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE),
                width=1,
            ),
            left_axis=fch.ChartAxis(
                label_size=60,
            ),
            bottom_axis=fch.ChartAxis(
                label_size=40,
                labels=bottom_axis_labels,
            ),
        )
        
        return chart
    
    def update_table(self):
        """Update the displayed chart and table based on current selections."""
        self.data_display.controls.clear()
        self.current_table = None
        
        filtered_data = self.load_and_filter_data()
        
        if filtered_data.empty:
            self.data_display.controls.append(
                ft.Container(
                    content=ft.Text("No data available for the selected criteria.", size=16, color="red"),
                    padding=20,
                )
            )
        else:
            # Get value columns for chart and legend
            date_col = "DATE"
            value_cols = [col for col in filtered_data.columns if col != date_col]
            
            # Create and display the line chart first
            chart = self.create_line_chart(filtered_data)
            self.data_display.controls.append(
                ft.Container(
                    content=chart,
                    padding=ft.Padding.only(bottom=10),
                )
            )
            
            # Add legend below the chart
            if value_cols:
                legend = self.create_legend(value_cols)
                self.data_display.controls.append(
                    ft.Container(
                        content=legend,
                        padding=ft.Padding.only(bottom=10),
                    )
                )
            
            # Add a divider between chart and table
            self.data_display.controls.append(ft.Divider())
            
            # Add table header
            self.data_display.controls.append(
                ft.Text("Data Table:", weight=ft.FontWeight.BOLD, size=14)
            )
            
            # Create table
            headers = [ft.DataColumn(ft.Text(col)) for col in filtered_data.columns]
            rows = []
            
            for _, row in filtered_data.iterrows():
                cells = [ft.DataCell(ft.Text(str(row[col]))) for col in filtered_data.columns]
                rows.append(ft.DataRow(cells=cells))
            
            # Use theme-aware colors for the table
            if self.is_dark_mode:
                heading_color = ft.Colors.GREY_800
                border_color = ft.Colors.GREY_700
            else:
                heading_color = ft.Colors.GREY_300
                border_color = ft.Colors.GREY_400
            
            table = ft.DataTable(
                columns=headers,
                rows=rows,
                sort_column_index=0,  # TIME_PERIOD column (index 0 in wide format)
                sort_ascending=False,
                heading_row_color=heading_color,
                heading_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.ELLIPSIS),
                border=ft.Border.all(1, border_color),
                expand=True
            )
            
            self.current_table = table
            self.data_display.controls.append(ft.Row([table], scroll= ft.ScrollMode.ALWAYS))
        
        self.page.update()
    
    async def export_to_excel(self, e):
        """Export current data to Excel."""
        if self.current_data is not None and not self.current_data.empty:
            filename = f"inflation_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            buffer = BytesIO()
            self.current_data.to_excel(buffer, index=False)
            excel_bytes = buffer.getvalue()
            buffer.close()
            _ = await ft.FilePicker().save_file(
                file_name=filename,
                file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["xlsx"],
                    src_bytes=excel_bytes,
                )
            self.page.show_dialog(ft.SnackBar(ft.Text(f"Data exported to {filename}")))
    
    def on_tab_change(self, e):
        """Clear data display when switching tabs."""
        self.data_display.controls.clear()
        self.current_table = None
        self.current_data = None
        self.page.update()
    
    # ===== Tab 1 Event Handlers =====
    
    def update_selected_coicops_tab1(self, e):
        """Handle COICOP checkbox changes for Tab 1."""
        self.tab1_selected_coicops = [cb.data for cb in self.coicop_checkboxes_tab1 if cb.value]
        self.update_table()
    
    def on_geo_change_tab1(self, e):
        """Handle geo dropdown change for Tab 1."""
        self.tab1_selected_geo = e.control.value if e.control.value else None
        self.update_table()
    
    # ===== Tab 2 Event Handlers =====
    
    def on_coicop_change_tab2(self, e):
        """Handle COICOP dropdown change for Tab 2."""
        self.tab2_selected_coicop = e.control.value if e.control.value else None
        self.update_table()
    
    def update_selected_geos_tab2(self, e):
        """Handle geo checkbox changes for Tab 2."""
        self.tab2_selected_geos = [cb.data for cb in self.geo_checkboxes_tab2 if cb.value]
        self.update_table()
    
    # ===== Common Event Handlers =====
    
    def on_unit_change(self, e):
        """Handle unit dropdown change."""
        self.selected_unit = e.control.value if e.control.value else None
        self.update_table()
    
    def update_from_date(self, e):
        """Handle from date input change."""
        self.from_date = e.control.value
        self.update_table()
    
    def update_to_date(self, e):
        """Handle to date input change."""
        self.to_date = e.control.value
        self.update_table()
    
    # ===== Search Filter Functions =====
    
    def filter_coicop_checkboxes_tab1(self, e):
        """Filter COICOP checkboxes in Tab 1 based on search text."""
        search_text = e.control.value.lower() if e.control.value else ""
        self.tab1_coicop_search_text = search_text
        
        # Clear current controls and add filtered checkboxes
        self.coicop_checkbox_container_tab1.controls.clear()
        
        for checkbox in self.coicop_checkboxes_tab1:
            # Get the label text (code - name format)
            label_text = checkbox.label.lower() if checkbox.label else ""
            # Check if search text matches
            if search_text in label_text:
                self.coicop_checkbox_container_tab1.controls.append(checkbox)
        
        self.page.update()
    
    def filter_geo_checkboxes_tab2(self, e):
        """Filter geo checkboxes in Tab 2 based on search text."""
        search_text = e.control.value.lower() if e.control.value else ""
        self.tab2_geo_search_text = search_text
        
        # Clear current controls and add filtered checkboxes
        self.geo_checkbox_container_tab2.controls.clear()
        
        for checkbox in self.geo_checkboxes_tab2:
            # Get the label text (code - name format)
            label_text = checkbox.label.lower() if checkbox.label else ""
            # Check if search text matches
            if search_text in label_text:
                self.geo_checkbox_container_tab2.controls.append(checkbox)
        
        self.page.update()
    
    def _create_ui_components(self):
        """Create all UI components."""
        
        # Data display area (main content - chart and table)
        self.data_display = ft.Column([], scroll=ft.ScrollMode.ALWAYS, expand=True)
        
        # ===== Tab 1 Controls =====
        
        # Search box for filtering COICOP checkboxes in Tab 1
        self.coicop_search_tab1 = ft.TextField(
            label="Search",
            hint_text="Type to filter items...",
            on_change=self.filter_coicop_checkboxes_tab1,
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            content_padding=ft.Padding(left=10, right=10, top=5, bottom=5),
        )
        
        # Multi-select COICOP checkboxes for Tab 1
        self.coicop_checkboxes_tab1 = []
        for option in self.coicop_options:
            checkbox = ft.Checkbox(label=f"{option.text}", value=False)
            checkbox.data = option.key
            checkbox.on_change = self.update_selected_coicops_tab1
            self.coicop_checkboxes_tab1.append(checkbox)
        
        # Container for COICOP checkboxes (will be populated dynamically based on search)
        self.coicop_checkbox_container_tab1 = ft.Column(
            self.coicop_checkboxes_tab1.copy(),
            scroll=ft.ScrollMode.AUTO
        )
        
        # Single geo dropdown for Tab 1
        self.geo_dropdown_tab1 = ft.Dropdown(
            label="Select Geography",
            options=self.geo_options,
            value=None,
            on_select=self.on_geo_change_tab1,
            expand=True,
            enable_filter=True,
            editable=True,
        )
        
        # ===== Tab 2 Controls =====
        
        # Single COICOP dropdown for Tab 2
        self.coicop_dropdown_tab2 = ft.Dropdown(
            label="Select ECOICOP Item",
            options=self.coicop_options,
            value=None,
            on_select=self.on_coicop_change_tab2,
            expand=True,
            enable_filter=True,
            editable=True,
        )
        
        # Search box for filtering geo checkboxes in Tab 2
        self.geo_search_tab2 = ft.TextField(
            label="Search",
            hint_text="Type to filter items...",
            on_change=self.filter_geo_checkboxes_tab2,
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            content_padding=ft.Padding(left=10, right=10, top=5, bottom=5),
        )
        
        # Multi-select geo checkboxes for Tab 2
        self.geo_checkboxes_tab2 = []
        for option in self.geo_options:
            checkbox = ft.Checkbox(label=f"{option.text}", value=False)
            checkbox.data = option.key
            checkbox.on_change = self.update_selected_geos_tab2
            self.geo_checkboxes_tab2.append(checkbox)
        
        # Container for geo checkboxes (will be populated dynamically based on search)
        self.geo_checkbox_container_tab2 = ft.Column(
            self.geo_checkboxes_tab2.copy(),
            scroll=ft.ScrollMode.AUTO
        )
        
        # ===== Common Controls =====
        
        self.unit_dropdown = ft.Dropdown(
            label="Select Unit",
            options=self.unit_options,
            value=None,
            on_select=self.on_unit_change,
            expand=True
        )
        
        self.from_date_input = ft.TextField(
            label="From Date (YYYY-MM)",
            on_change=self.update_from_date,
            expand=True,
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]{0,4}(-[0-9]{0,2})?$", replacement_string="")
        )
        
        self.to_date_input = ft.TextField(
            label="To Date (YYYY-MM)",
            on_change=self.update_to_date,
            expand=True,
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]{0,4}(-[0-9]{0,2})?$", replacement_string="")
        )
        
        self.export_button = ft.Button(
            "Export to Excel",
            on_click=self.export_to_excel,
            icon=ft.Icons.FILE_DOWNLOAD
        )
    
    def main(self, page: ft.Page):
        """Main entry point for the Flet application."""
        self.page = page
        
        # Page configuration
        page.title = "Inflation Data Explorer"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 0  # Remove padding for full-width app bar
        page.scroll = ft.ScrollMode.AUTO
        
        # Create UI components
        self._create_ui_components()
        
        # ===== Tab Layouts =====
        
        tab1_content = ft.Column([
            ft.Text("Select ECOICOP Items:", weight=ft.FontWeight.BOLD, size=12),
            self.coicop_search_tab1,
            ft.Container(
                content=self.coicop_checkbox_container_tab1,
                height=150,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=5,
            ),
            ft.Container(height=10),
            self.geo_dropdown_tab1,
        ], 
            scroll=ft.ScrollMode.AUTO,
        )
        
        tab2_content = ft.Column([
            self.coicop_dropdown_tab2,
            ft.Container(height=10),
            ft.Text("Select Geographies:", weight=ft.FontWeight.BOLD, size=12),
            self.geo_search_tab2,
            ft.Container(
                content=self.geo_checkbox_container_tab2,
                height=150,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=5,
            ),
        ], 
            scroll=ft.ScrollMode.AUTO,
        )
        
        # ===== Tabs =====
        self.tabs = ft.Tabs(
            selected_index=0,
            length=2,
            on_change=self.on_tab_change,
            content=ft.Column(
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label="By Geography"),
                            ft.Tab(label="By ECOICOP v2"),
                        ]
                    ),
                    ft.TabBarView(
                        controls=[tab1_content, tab2_content],
                        height=300,
                    ),
                ],
                expand=True
            ),
        )
        
        # ===== Sidebar Toggle Button =====
        self.toggle_button = ft.IconButton(
            icon=ft.Icons.MENU_OPEN,
            on_click=self.toggle_sidebar,
            tooltip="Toggle sidebar",
        )
        
        # ===== Sidebar Content =====
        self.sidebar_content = ft.Column([
            self.tabs,
            ft.Divider(),
            self.unit_dropdown,
            ft.Container(height=10),
            ft.Row([self.from_date_input, self.to_date_input]),
            ft.Container(height=10),
            self.export_button,
        ], 
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        # ===== Collapsible Sidebar =====
        self.sidebar = ft.Container(
            content=ft.Column([
                ft.Row([self.toggle_button], alignment=ft.MainAxisAlignment.END),
                self.sidebar_content,
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            width=self.sidebar_width_expanded,
            bgcolor=ft.Colors.GREY_50,
            border=ft.Border(right=ft.BorderSide(1, ft.Colors.GREY_300)),
            padding=10,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        
        # ===== Main Content Area =====
        main_content = ft.Container(
            content=self.data_display,
            expand=True,
            padding=20,
        )
        
        # ===== App Bar =====
        last_update = self.get_last_update_date()
        
        # Theme toggle button
        self.theme_toggle_button = ft.IconButton(
            icon=ft.Icons.DARK_MODE,
            on_click=self.toggle_theme,
            tooltip="Switch to dark mode",
        )
        
        # Create app bar components with references for theme switching
        self.app_bar_title = ft.Text("Inflation Data Explorer", size=20, weight=ft.FontWeight.BOLD)
        self.last_update_icon = ft.Icon(ft.Icons.UPDATE, size=16, color=ft.Colors.GREY_600)
        self.last_update_text = ft.Text(f"Last update: {last_update}", size=12, color=ft.Colors.GREY_600)
        
        self.app_bar = ft.Container(
            content=ft.Row([
                self.app_bar_title,
                ft.Container(expand=True),
                ft.Row([
                    self.last_update_icon,
                    self.last_update_text,
                ], spacing=5),
                self.theme_toggle_button,
            ], 
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.BLUE_50,
            padding=ft.Padding(left=20, right=20, top=10, bottom=10),
            border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
        )
        
        # ===== Main Layout Row =====
        main_row = ft.Row([
            self.sidebar,
            main_content,
        ], 
            expand=True, 
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        
        # ===== Page Layout =====
        page.add(
            ft.Column([
                self.app_bar,
                main_row,
            ], 
                expand=True,
            )
        )


if __name__ == "__main__":
    app = InflationDataExplorer()
    ft.run(main=app.main)