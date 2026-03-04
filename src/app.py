"""
PyScript Inflation Data Explorer
A web application for exploring inflation data using Altair charts.
"""

import pandas as pd
import altair as alt
from io import BytesIO
from pyscript import document, window, fetch
from html import escape
import json

# ============================================================================
# DATA LOADING
# ============================================================================

# Load mapping files at startup (using relative paths from HTML location)
coicop_map = pd.read_csv('coicop18.csv')
geo_map = pd.read_csv('geo.csv')
unit_map = pd.read_csv('unit.csv')

# Load last update date
with open('last_update.txt', 'r') as f:
    last_update = f.read().strip()

# Cache for loaded data files
data_cache = {}

async def load_data(file_name):
    """
    Load data file on-demand (lazy loading) with caching.
    
    Args:
        file_name: Name of the file without extension (e.g., 'IT' or 'CP01')
    
    Returns:
        pandas DataFrame with the data
    """
    if file_name not in data_cache:
        try:
            data_cache[file_name] = pd.read_csv(await fetch(f'./assets/data/{file_name}.csv'))
        except FileNotFoundError:
            print(f"Warning: Data file {file_name}.csv not found")
            return pd.DataFrame()
    return data_cache[file_name].copy()

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

# Global application state
state = {
    'active_tab': 'geography',  # 'geography' or 'coicop'
    'selected_geo': None,
    'selected_coicops': [],
    'selected_coicop': None,
    'selected_geos': [],
    'selected_unit': 'I25',
    'from_date': '',
    'to_date': '',
    'current_data': None,
    'full_coicop_list': [],
    'full_geo_list': []
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_element(element_id):
    """Get DOM element by ID."""
    return document.getElementById(element_id)

def set_element_html(element_id, html_content):
    """Set HTML content of an element."""
    element = get_element(element_id)
    if element:
        element.innerHTML = html_content

def show_loading(show=True):
    """Show or hide loading overlay."""
    overlay = get_element('loading-overlay')
    if overlay:
        overlay.style.display = 'flex' if show else 'none'

def get_selected_checkboxes(container_id):
    """Get list of selected checkbox values from a container."""
    container = get_element(container_id)
    if not container:
        return []
    
    selected = []
    checkboxes = container.querySelectorAll('input[type="checkbox"]:checked')
    for cb in checkboxes:
        selected.append(cb.value)
    return selected

def create_checkbox_item(value, label, checked=False):
    """Create HTML for a checkbox item."""
    checked_attr = 'checked' if checked else ''
    value_escaped = escape(value, quote=True)
    label_escaped = escape(label, quote=True)
    # Note: Using onchange attribute for dynamic elements (py-change doesn't work for dynamically added elements)
    return f'''
    <div class="form-check">
        <input class="form-check-input" type="checkbox" value="{value_escaped}"
               id="cb-{value_escaped}" {checked_attr} onchange="window._py_checkbox_change()">
        <label class="form-check-label" for="cb-{value_escaped}" title="{label_escaped}">
            {label_escaped}
        </label>
    </div>
    '''

# ============================================================================
# INITIALIZATION
# ============================================================================

def populate_dropdowns():
    """Populate all dropdown menus from mapping data."""
    # Populate geography dropdown
    geo_select = get_element('geo-select')
    if geo_select:
        options = ['<option value="">Select a geography...</option>']
        for _, row in geo_map.iterrows():
            code_escaped = escape(row["code"], quote=True)
            name_escaped = escape(row["name"], quote=True)
            options.append(f'<option value="{code_escaped}">{name_escaped} ({code_escaped})</option>')
        geo_select.innerHTML = ''.join(options)
    
    # Populate COICOP dropdown (for Tab 2)
    coicop_select = get_element('coicop-select')
    if coicop_select:
        options = ['<option value="">Select a category...</option>']
        # Filter to level 2 categories for the dropdown
        level2_coicop = coicop_map[coicop_map['level'] == 2]
        for _, row in level2_coicop.iterrows():
            code_escaped = escape(row["code"], quote=True)
            name_escaped = escape(row["name"], quote=True)
            options.append(f'<option value="{code_escaped}">{name_escaped} ({code_escaped})</option>')
        coicop_select.innerHTML = ''.join(options)
    
    # Populate unit dropdown
    unit_select = get_element('unit-select')
    if unit_select:
        options = []
        for _, row in unit_map.iterrows():
            code_escaped = escape(row["code"], quote=True)
            name_escaped = escape(row["name"], quote=True)
            selected = 'selected' if row['code'] == state['selected_unit'] else ''
            options.append(f'<option value="{code_escaped}" {selected}>{name_escaped}</option>')
        unit_select.innerHTML = ''.join(options)

def populate_coicop_checkboxes(search_filter=''):
    """Populate COICOP checkbox list for Tab 1."""
    container = get_element('coicop-list-geo')
    if not container:
        return
    
    # Get level 2 categories
    level2_coicop = coicop_map[coicop_map['level'] == 2].copy()
    
    # Apply search filter
    if search_filter:
        mask = level2_coicop['name'].str.lower().str.contains(search_filter.lower()) | \
               level2_coicop['code'].str.lower().str.contains(search_filter.lower())
        level2_coicop = level2_coicop[mask]
    
    # Store full list for reference
    state['full_coicop_list'] = level2_coicop['code'].tolist()
    
    # Generate checkboxes
    html_parts = []
    for _, row in level2_coicop.iterrows():
        checked = row['code'] in state['selected_coicops']
        html_parts.append(create_checkbox_item(row['code'], f"{row['name']} ({row['code']})", checked))
    
    container.innerHTML = ''.join(html_parts)

def populate_geo_checkboxes(search_filter=''):
    """Populate geography checkbox list for Tab 2."""
    container = get_element('geo-list-coicop')
    if not container:
        return
    
    geos = geo_map.copy()
    
    # Apply search filter
    if search_filter:
        mask = geos['name'].str.lower().str.contains(search_filter.lower()) | \
               geos['code'].str.lower().str.contains(search_filter.lower())
        geos = geos[mask]
    
    # Store full list for reference
    state['full_geo_list'] = geos['code'].tolist()
    
    # Generate checkboxes
    html_parts = []
    for _, row in geos.iterrows():
        checked = row['code'] in state['selected_geos']
        html_parts.append(create_checkbox_item(row['code'], f"{row['name']} ({row['code']})", checked))
    
    container.innerHTML = ''.join(html_parts)

def display_last_update():
    """Display last update date in header."""
    element = get_element('last-update')
    if element:
        element.textContent = last_update

# ============================================================================
# DATA FILTERING
# ============================================================================

async def filter_data():
    """
    Filter data based on current state.
    
    Returns:
        Filtered DataFrame in wide format with TIME_PERIOD as index
    """
    show_loading(True)
    
    try:
        if state['active_tab'] == 'geography':
            # Tab 1: Load geo file, filter by coicops
            if not state['selected_geo']:
                return None
            
            df = await load_data(state['selected_geo'])
            if df.empty:
                return None
            
            # Get selected COICOPs from checkboxes
            state['selected_coicops'] = get_selected_checkboxes('coicop-list-geo')
            
            if state['selected_coicops']:
                df = df[df['coicop18'].isin(state['selected_coicops'])]
            
        else:  # 'coicop' tab
            # Tab 2: Load coicop file, filter by geos
            if not state['selected_coicop']:
                return None
            
            df = await load_data(state['selected_coicop'])
            if df.empty:
                return None
            
            # Get selected geos from checkboxes
            state['selected_geos'] = get_selected_checkboxes('geo-list-coicop')
            
            if state['selected_geos']:
                df = df[df['geo'].isin(state['selected_geos'])]
        
        # Apply unit filter
        if state['selected_unit']:
            df = df[df['unit'] == state['selected_unit']]
        
        # Apply date range filter
        if state['from_date']:
            df = df[df['TIME_PERIOD'] >= state['from_date']]
        if state['to_date']:
            df = df[df['TIME_PERIOD'] <= state['to_date']]
        
        if df.empty:
            return None
        
        # Create series identifier based on active tab
        if state['active_tab'] == 'geography':
            # Series = COICOP categories
            df['series'] = df['coicop18']
        else:
            # Series = Geographies
            df['series'] = df['geo']
        
        # Pivot to wide format
        df_pivot = df.pivot_table(
            index='TIME_PERIOD',
            columns='series',
            values='value',
            aggfunc='first'
        ).reset_index()
        
        # Rename columns from codes to names
        rename_map = {}
        if state['active_tab'] == 'geography':
            for _, row in coicop_map.iterrows():
                rename_map[row['code']] = row['name']
        else:
            for _, row in geo_map.iterrows():
                rename_map[row['code']] = row['name']
        
        df_pivot = df_pivot.rename(columns=rename_map)
        
        state['current_data'] = df_pivot
        return df_pivot
        
    except Exception as e:
        print(f"Error filtering data: {e}")
        # Show user-facing error message
        set_element_html('chart-area', f'''
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Error loading data:</strong> {escape(str(e))}
            </div>
        ''')
        return None
    finally:
        show_loading(False)

# ============================================================================
# CHART CREATION
# ============================================================================

def create_chart(df):
    """
    Create Altair line chart from DataFrame.
    
    Args:
        df: Wide-format DataFrame with TIME_PERIOD and value columns
    
    Returns:
        Altair Chart object
    """
    if df is None or df.empty:
        return None
    
    # Melt DataFrame to long format for Altair
    id_vars = ['TIME_PERIOD']
    value_vars = [col for col in df.columns if col not in id_vars]
    
    df_melted = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name='series',
        value_name='value'
    )
    
    # Convert TIME_PERIOD to proper date format
    df_melted['TIME_PERIOD'] = pd.to_datetime(df_melted['TIME_PERIOD'] + '-01')
    
    # Create chart
    chart = alt.Chart(df_melted).mark_line().encode(
        x=alt.X('TIME_PERIOD:T', title='Date'),
        y=alt.Y('value:Q', title='Value'),
        color=alt.Color('series:N', title='Series'),
        tooltip=['TIME_PERIOD:T', alt.Tooltip('value:Q', format='.1f'), 'series:N']
    ).properties(
        width='container',
        height=400
    ).interactive()
    
    return chart

def render_chart(chart):
    """Render Altair chart to the chart container."""
    container = get_element('chart-area')
    if not container:
        return
    
    if chart is None:
        container.innerHTML = '''
            <div class="placeholder-message">
                <i class="bi bi-graph-up"></i>
                <p>No data available for the selected filters</p>
            </div>
        '''
        return
    
    # Save chart as HTML and embed
    chart_html = chart.to_html()
    container.innerHTML = f'<div class="chart-wrapper">{chart_html}</div>'

# ============================================================================
# TABLE CREATION
# ============================================================================

def create_table(df):
    """
    Create HTML table from DataFrame.
    
    Args:
        df: Wide-format DataFrame
    
    Returns:
        HTML string for the table
    """
    if df is None or df.empty:
        return '''
            <div class="placeholder-message">
                <i class="bi bi-table"></i>
                <p>No data to display</p>
            </div>
        '''
    
    # Sort by date descending
    df = df.sort_values('TIME_PERIOD', ascending=False)
    
    # Format numeric columns to 1 decimal place
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    
    # Build HTML table
    html_parts = ['<table class="table table-striped table-bordered table-hover">']
    
    # Header
    html_parts.append('<thead><tr>')
    for col in df.columns:
        html_parts.append(f'<th>{escape(str(col))}</th>')
    html_parts.append('</tr></thead>')
    
    # Body
    html_parts.append('<tbody>')
    for _, row in df.iterrows():
        html_parts.append('<tr>')
        for col in df.columns:
            val = row[col]
            if col in numeric_cols:
                if pd.isna(val):
                    formatted = '-'
                else:
                    formatted = f'{val:.1f}'
            else:
                formatted = escape(str(val))
            html_parts.append(f'<td>{formatted}</td>')
        html_parts.append('</tr>')
    html_parts.append('</tbody></table>')
    
    return ''.join(html_parts)

def render_table(df):
    """Render data table to the table container."""
    container = get_element('table-area')
    row_count = get_element('row-count')
    
    if container:
        html = create_table(df)
        container.innerHTML = html
    
    if row_count:
        if df is not None and not df.empty:
            row_count.textContent = f'{len(df)} rows'
        else:
            row_count.textContent = '0 rows'

# ============================================================================
# EXCEL EXPORT
# ============================================================================

def export_to_excel(df):
    """
    Export DataFrame to Excel and trigger download.
    
    Args:
        df: DataFrame to export
    """
    if df is None or df.empty:
        return
    
    try:
        # Create Excel file in memory
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl', sheet_name='Inflation Data')
        buffer.seek(0)
        
        # Convert to base64 for download
        import base64
        b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Create download link using JavaScript
        js_code = f'''
        var link = document.createElement('a');
        link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_data}';
        link.download = 'inflation_data.xlsx';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        '''
        
        window.eval(js_code)
        
    except Exception as e:
        print(f"Error exporting to Excel: {e}")

# ============================================================================
# EVENT HANDLERS
# ============================================================================

def on_tab_change(tab_id):
    """Handle tab change event."""
    state['active_tab'] = tab_id
    
    # Clear selections when switching tabs
    if tab_id == 'geography':
        state['selected_coicop'] = None
        state['selected_geos'] = []
    else:
        state['selected_geo'] = None
        state['selected_coicops'] = []
    
    # Call async refresh_data
    from pyscript import asyncio
    asyncio.ensure_future(refresh_data())

def on_geo_select(event=None):
    """Handle geography dropdown selection."""
    select = get_element('geo-select')
    if select:
        state['selected_geo'] = select.value if select.value else None
        from pyscript import asyncio
        asyncio.ensure_future(refresh_data())

def on_coicop_select(event=None):
    """Handle COICOP dropdown selection."""
    select = get_element('coicop-select')
    if select:
        state['selected_coicop'] = select.value if select.value else None
        from pyscript import asyncio
        asyncio.ensure_future(refresh_data())

def on_unit_select(event=None):
    """Handle unit dropdown selection."""
    select = get_element('unit-select')
    if select:
        state['selected_unit'] = select.value if select.value else None
        from pyscript import asyncio
        asyncio.ensure_future(refresh_data())

def on_date_change(event=None):
    """Handle date input changes."""
    from_input = get_element('from-date')
    to_input = get_element('to-date')
    
    if from_input:
        state['from_date'] = from_input.value if from_input.value else ''
    if to_input:
        state['to_date'] = to_input.value if to_input.value else ''
    
    from pyscript import asyncio
    asyncio.ensure_future(refresh_data())

def on_checkbox_change(event=None):
    """Handle checkbox changes."""
    from pyscript import asyncio
    asyncio.ensure_future(refresh_data())

def on_coicop_search_geo(event=None):
    """Handle search filter for COICOP list in Tab 1."""
    search_input = get_element('coicop-search-geo')
    if search_input:
        populate_coicop_checkboxes(search_input.value)

def on_geo_search_coicop(event=None):
    """Handle search filter for geography list in Tab 2."""
    search_input = get_element('geo-search-coicop')
    if search_input:
        populate_geo_checkboxes(search_input.value)

def on_export_click(event=None):
    """Handle export button click."""
    if state['current_data'] is not None:
        export_to_excel(state['current_data'])

def on_theme_toggle(event=None):
    """Handle theme toggle button click."""
    html = document.documentElement
    theme_icon = get_element('theme-icon')
    
    if html.getAttribute('data-theme') == 'dark':
        html.setAttribute('data-theme', 'light')
        if theme_icon:
            theme_icon.className = 'bi bi-moon-fill'
    else:
        html.setAttribute('data-theme', 'dark')
        if theme_icon:
            theme_icon.className = 'bi bi-sun-fill'

# ============================================================================
# REFRESH DATA
# ============================================================================

async def refresh_data():
    """Refresh chart and table based on current state."""
    export_btn = get_element('export-btn')
    
    # Determine if we have enough selections to load data
    if state['active_tab'] == 'geography':
        has_selection = state['selected_geo'] is not None
    else:
        has_selection = state['selected_coicop'] is not None
    
    if not has_selection:
        # Clear displays
        render_chart(None)
        render_table(None)
        state['current_data'] = None
        if export_btn:
            export_btn.disabled = True
        return
    
    # Filter and display data
    df = await filter_data()
    
    if df is not None and not df.empty:
        chart = create_chart(df)
        render_chart(chart)
        render_table(df)
        if export_btn:
            export_btn.disabled = False
    else:
        render_chart(None)
        render_table(None)
        state['current_data'] = None
        if export_btn:
            export_btn.disabled = True

# ============================================================================
# MAIN INITIALIZATION
# ============================================================================

def on_checkbox_change_wrapper():
    """Wrapper for checkbox change to call async refresh_data."""
    from pyscript import asyncio
    asyncio.ensure_future(refresh_data())

def main():
    """Main initialization function."""
    # Display last update date
    display_last_update()
    
    # Populate all dropdowns
    populate_dropdowns()
    
    # Populate checkbox lists
    populate_coicop_checkboxes()
    populate_geo_checkboxes()
    
    # Set up global checkbox change handler for dynamically created checkboxes
    window._py_checkbox_change = on_checkbox_change_wrapper
    
    # Note: Theme toggle is handled via py-click attribute in HTML
    
    # Initial render (empty state)
    render_chart(None)
    render_table(None)
    
    print("Inflation Data Explorer initialized successfully!")

# Run main on load
main()
