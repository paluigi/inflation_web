import {
    registerServiceWorker, initDuckDB, fetchCSV, initSelect,
    parseDateBoundary, renderOutput, initThemeToggle, initTabs,
    setActiveNavLink
} from './common.js';
import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.28.0/+esm';

const myChartRef = { value: null };
let currentData = [];
let activeTab = 'tab1';
const maps = { geo: {}, nace_r2: {}, unit: {} };

const UI = {
    btnQuery: document.getElementById('btn-query'),
    btnExport: document.getElementById('btn-export'),
    status: document.getElementById('status'),
    tbody: document.querySelector('#data-table tbody'),
    tableHead: document.querySelector('#data-table thead'),
    ctx: document.getElementById('myChart').getContext('2d'),
    t1Nace: null, t1Geo: null, t2Geo: null, t2Nace: null, sharedUnit: null
};

async function init() {
    try {
        registerServiceWorker();
        initThemeToggle(myChartRef);
        initTabs();
        setActiveNavLink('ppi');

        const { db, conn } = await initDuckDB();
        UI._db = db;
        UI._conn = conn;

        fetch('./assets/ppi_last_update.txt')
            .then(res => res.ok ? res.text() : "Unknown")
            .then(text => document.getElementById('last-update').innerText = `Last Update: ${text}`)
            .catch(() => {});

        UI.status.innerText = "Loading dictionaries...";
        const [geoData, naceData, unitData] = await Promise.all([
            fetchCSV('./assets/maps/geo_ppi.csv'),
            fetchCSV('./assets/maps/nace_r2.csv'),
            fetchCSV('./assets/maps/unit_ppi.csv')
        ]);

        UI.t1Nace = initSelect('#t1-nace', naceData, 'nace_r2', false, maps);
        UI.t1Geo = initSelect('#t1-geo', geoData, 'geo', true, maps);
        UI.t2Geo = initSelect('#t2-geo', geoData, 'geo', false, maps);
        UI.t2Nace = initSelect('#t2-nace', naceData, 'nace_r2', true, maps);
        UI.sharedUnit = initSelect('#shared-unit', unitData, 'unit', false, maps);

        if (naceData.length > 0) UI.t1Nace.setValue(naceData[1].code);
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

        let whereClauses = [`UNIT = '${unit}'`];
        let singleTitleName = "";
        let groupDimension = "";

        if (activeTab === 'tab1') {
            const nace = UI.t1Nace.getValue();
            const geos = UI.t1Geo.getValue();
            if (!nace || geos.length === 0) throw new Error("Please select a NACE R2 category and at least one Geo.");

            singleTitleName = maps.nace_r2[nace];
            groupDimension = "geo";

            whereClauses.push(`nace_r2 = '${nace}'`);
            whereClauses.push(`geo IN (${geos.map(g => `'${g}'`).join(',')})`);
        } else {
            const geo = UI.t2Geo.getValue();
            const naces = UI.t2Nace.getValue();
            if (!geo || naces.length === 0) throw new Error("Please select a Geo and at least one NACE R2 category.");

            singleTitleName = maps.geo[geo];
            groupDimension = "nace_r2";

            whereClauses.push(`geo = '${geo}'`);
            whereClauses.push(`nace_r2 IN (${naces.map(n => `'${n}'`).join(',')})`);
        }

        if (dFrom) whereClauses.push(`TIME_PERIOD >= '${dFrom}'`);
        if (dTo) whereClauses.push(`TIME_PERIOD <= '${dTo}'`);

        const parquetUrl = new URL('./assets/data/ppi_data.parquet', window.location.href).href;
        await UI._db.registerFileURL('ppi_data.parquet', parquetUrl, duckdb.DuckDBDataProtocol.HTTP, false);

        const query = `
            PIVOT (
                SELECT TIME_PERIOD as date, ${groupDimension}, CAST(obsValue AS FLOAT) as value
                FROM read_parquet('ppi_data.parquet')
                WHERE ${whereClauses.join(' AND ')}
            )
            ON ${groupDimension}
            USING first(value)
            ORDER BY date ASC
        `;

        const result = await UI._conn.query(query);
        const rawData = result.toArray().map(r => r.toJSON());

        const mapToUse = groupDimension === 'geo' ? maps.geo : maps.nace_r2;

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
            groupDimension === 'geo' ? 'geo' : 'nace_r2',
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
    XLSX.writeFile(workbook, "ppi_data.xlsx");
});

init();
