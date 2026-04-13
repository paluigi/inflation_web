import {
    registerServiceWorker, initDuckDB, fetchCSV, initSelect,
    parseDateBoundary, renderOutput, initThemeToggle, initTabs,
    setActiveNavLink, CHART_COLORS
} from './common.js';
import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.28.0/+esm';

const myChartRef = { value: null };
let currentData = [];
let activeTab = 'tab1';
const maps = { geo: {}, coicop: {}, unit: {} };

const UI = {
    btnQuery: document.getElementById('btn-query'),
    btnExport: document.getElementById('btn-export'),
    status: document.getElementById('status'),
    tbody: document.querySelector('#data-table tbody'),
    tableHead: document.querySelector('#data-table thead'),
    ctx: document.getElementById('myChart').getContext('2d'),
    t1Coicop: null, t1Geo: null, t2Geo: null, t2Coicop: null, sharedUnit: null
};

async function init() {
    try {
        registerServiceWorker();
        initThemeToggle(myChartRef);
        initTabs();
        setActiveNavLink('hicp');

        const { db, conn } = await initDuckDB();
        UI._db = db;
        UI._conn = conn;

        fetch('./assets/last_update.txt')
            .then(res => res.ok ? res.text() : "Unknown")
            .then(text => document.getElementById('last-update').innerText = `Last Update: ${text}`)
            .catch(() => {});

        UI.status.innerText = "Loading dictionaries...";
        const [geoData, coicopData, unitData] = await Promise.all([
            fetchCSV('./assets/maps/geo.csv'),
            fetchCSV('./assets/maps/coicop18.csv'),
            fetchCSV('./assets/maps/unit.csv')
        ]);

        UI.t1Coicop = initSelect('#t1-coicop', coicopData, 'coicop', false, maps);
        UI.t1Geo = initSelect('#t1-geo', geoData, 'geo', true, maps);
        UI.t2Geo = initSelect('#t2-geo', geoData, 'geo', false, maps);
        UI.t2Coicop = initSelect('#t2-coicop', coicopData, 'coicop', true, maps);
        UI.sharedUnit = initSelect('#shared-unit', unitData, 'unit', false, maps);

        if (coicopData.length > 0) UI.t1Coicop.setValue(coicopData[1].code);
        if (unitData.length > 0) UI.sharedUnit.setValue(unitData[1].code);

        UI.status.innerText = "Engine Ready.";
        UI.btnQuery.disabled = false;
    } catch (err) {
        console.error(err);
        UI.status.innerText = "Error: " + err.message;
    }
}

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        activeTab = tab.getAttribute('data-target');
    });
});

UI.btnQuery.addEventListener('click', async () => {
    UI.status.innerText = "Querying Data...";
    UI.btnQuery.disabled = true;

    try {
        const unit = UI.sharedUnit.getValue();
        const dFrom = parseDateBoundary(document.getElementById('date-from').value, false);
        const dTo = parseDateBoundary(document.getElementById('date-to').value, true);

        let whereClauses = [`unit = '${unit}'`];
        let singleTitleName = "";
        let groupDimension = "";

        if (activeTab === 'tab1') {
            const coicop = UI.t1Coicop.getValue();
            const geos = UI.t1Geo.getValue();
            if (!coicop || geos.length === 0) throw new Error("Please select a COICOP and at least one Geo.");

            singleTitleName = maps.coicop[coicop];
            groupDimension = "geo";

            whereClauses.push(`coicop18 = '${coicop}'`);
            whereClauses.push(`geo IN (${geos.map(g => `'${g}'`).join(',')})`);
        } else {
            const geo = UI.t2Geo.getValue();
            const coicops = UI.t2Coicop.getValue();
            if (!geo || coicops.length === 0) throw new Error("Please select a Geo and at least one COICOP.");

            singleTitleName = maps.geo[geo];
            groupDimension = "coicop18";

            whereClauses.push(`geo = '${geo}'`);
            whereClauses.push(`coicop18 IN (${coicops.map(c => `'${c}'`).join(',')})`);
        }

        if (dFrom) whereClauses.push(`TIME_PERIOD >= '${dFrom}'`);
        if (dTo) whereClauses.push(`TIME_PERIOD <= '${dTo}'`);

        const parquetUrl = new URL('./assets/data/hicp_data.parquet', window.location.href).href;
        await UI._db.registerFileURL('hicp_data.parquet', parquetUrl, duckdb.DuckDBDataProtocol.HTTP, false);

        const query = `
            PIVOT (
                SELECT TIME_PERIOD as date, ${groupDimension}, CAST(value AS FLOAT) as value
                FROM read_parquet('hicp_data.parquet')
                WHERE ${whereClauses.join(' AND ')}
            )
            ON ${groupDimension}
            USING first(value)
            ORDER BY date ASC
        `;

        const result = await UI._conn.query(query);
        const rawData = result.toArray().map(r => r.toJSON());

        const mapToUse = groupDimension === 'geo' ? maps.geo : maps.coicop;

        currentData = rawData.map(row => {
            const newRow = { 'Time Period': row.date };
            for (const key in row) {
                if (key !== 'date') {
                    const descriptiveName = mapToUse[key] || key;
                    newRow[descriptiveName] = row[key];
                }
            }
            return newRow;
        });

        renderOutput(currentData, singleTitleName, groupDimension, maps,
            groupDimension === 'geo' ? 'geo' : 'coicop',
            UI.tbody, UI.tableHead, UI.ctx, myChartRef);
        UI.status.innerText = `Loaded ${currentData.length} periods.`;
        UI.btnExport.disabled = false;

    } catch (err) {
        console.error(err);
        UI.status.innerText = "Error: " + err.message;
    } finally {
        UI.btnQuery.disabled = false;
    }
});

UI.btnExport.addEventListener('click', () => {
    if (!currentData || currentData.length === 0) return;
    const worksheet = XLSX.utils.json_to_sheet(currentData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Data");
    XLSX.writeFile(workbook, "hicp_inflation_data.xlsx");
});

init();
