import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.28.0/+esm';

export const CHART_COLORS = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c', '#34495e'];

export function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('./sw.js')
                .then(registration => {
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                })
                .catch(error => {
                    console.log('ServiceWorker registration failed: ', error);
                });
        });
    }
}

export async function initDuckDB() {
    const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
    const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);
    const worker = new Worker(URL.createObjectURL(new Blob([`importScripts("${bundle.mainWorker}");`], {type: 'text/javascript'})));
    const logger = new duckdb.ConsoleLogger();
    const db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    const conn = await db.connect();
    return { db, conn };
}

export async function fetchCSV(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to load ${path}`);
    const text = await res.text();
    return new Promise(resolve => {
        Papa.parse(text, {
            header: true, skipEmptyLines: true,
            complete: function(results) { resolve(results.data); }
        });
    });
}

export function initSelect(selector, data, mapKey, isMultiple, maps) {
    const options = data.map(row => {
        maps[mapKey][row.code] = row.name;
        return { value: row.code, text: `${row.code} - ${row.name}` };
    });

    return new TomSelect(selector, {
        options: options,
        maxItems: isMultiple ? null : 1,
        valueField: 'value',
        labelField: 'text',
        searchField: ['value', 'text'],
        plugins: isMultiple ? ['remove_button'] : []
    });
}

export function parseDateBoundary(dateStr, isEnd) {
    if (!dateStr) return null;
    let val = dateStr.trim();
    if (/^\d{4}$/.test(val)) return isEnd ? `${val}-12` : `${val}-01`;
    if (/^\d{4}-\d{2}$/.test(val)) return val;
    return null;
}

export function renderOutput(data, titlePrefix, groupDimension, maps, mapKey, tbody, tableHead, ctx, myChartRef) {
    tbody.innerHTML = '';
    tableHead.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="2" style="text-align:center; padding: 20px; color: var(--text-muted);">No data found.</td></tr>`;
        if (myChartRef.value) myChartRef.value.destroy();
        return;
    }

    const columns = Object.keys(data[0]).filter(k => k !== 'Time Period');

    let headerHTML = '<tr><th>Time Period</th>';
    columns.forEach(colName => {
        headerHTML += `<th>${colName}</th>`;
    });
    headerHTML += '</tr>';
    tableHead.innerHTML = headerHTML;

    [...data].reverse().forEach(row => {
        const tr = document.createElement('tr');
        let rowHTML = `<td><strong>${row['Time Period']}</strong></td>`;
        columns.forEach(colName => {
            const val = row[colName];
            rowHTML += `<td>${val !== null && val !== undefined ? val.toFixed(2) : '-'}</td>`;
        });
        tr.innerHTML = rowHTML;
        tbody.appendChild(tr);
    });

    const uniqueDates = data.map(d => d['Time Period']);

    const datasets = columns.map((colName, index) => {
        return {
            label: colName,
            data: data.map(row => row[colName] !== undefined ? row[colName] : null),
            borderColor: CHART_COLORS[index % CHART_COLORS.length],
            backgroundColor: CHART_COLORS[index % CHART_COLORS.length] + '33',
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            spanGaps: true
        };
    });

    if (myChartRef.value) myChartRef.value.destroy();

    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    Chart.defaults.color = isDarkMode ? '#e9e9e9' : '#666';

    myChartRef.value = new Chart(ctx, {
        type: 'line',
        data: { labels: uniqueDates, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                title: { display: true, text: `Data for: ${titlePrefix}`, font: { size: 16 } },
                legend: { position: 'bottom' }
            }
        }
    });
}

export function initThemeToggle(myChartRef) {
    document.getElementById('theme-toggle').addEventListener('click', () => {
        const html = document.documentElement;
        const isDark = html.getAttribute('data-theme') === 'dark';
        html.setAttribute('data-theme', isDark ? 'light' : 'dark');
        if (myChartRef.value) {
            Chart.defaults.color = isDark ? '#666' : '#e9e9e9';
            myChartRef.value.update();
        }
    });
}

export function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.getAttribute('data-target');
            document.getElementById(target).classList.add('active');
        });
    });
}

export function setActiveNavLink(pageId) {
    const link = document.querySelector(`.nav-links a[data-page="${pageId}"]`);
    if (link) link.classList.add('active');
}
