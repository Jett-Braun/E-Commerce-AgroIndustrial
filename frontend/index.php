<?php 
include 'includes/header.php'; 

// Lectura de referencias del dataset.csv para el dashboard
$market_data = [];
if (file_exists('../api_python/dataset.csv')) {
    $file = fopen('../api_python/dataset.csv', 'r');
    $header = fgetcsv($file);
    while (($row = fgetcsv($file)) !== FALSE) {
        $market_data[] = array_combine($header, $row);
    }
    fclose($file);
    $last_record = end($market_data); // Último registro del mercado
} else {
    // Valores de respaldo si no encuentra el CSV
    $last_record = ['diesel_usd_l' => '0.80', 'cafe_usd_qq' => '258.90', 'aguacate_usd_kg' => '2.95', 'elec_us_kwh' => '0.136'];
}
?>

<style>
    .hero { text-align: center; margin-bottom: 30px; }
    .grid-services { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 20px; }
    .card { background: #fafafa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 20px; text-align: center; }
    .card h3 { color: #2e7d32; margin-top: 0; }
    .card-btn { display: inline-block; background-color: #2e7d32; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; font-weight: bold; margin-top: 15px; }
    .card-btn:hover { background-color: #1b5e20; }
    .market-ticker { background: #f1f8e9; border: 1px solid #c8e6c9; border-radius: 6px; padding: 15px; margin-bottom: 25px; }
    .ticker-grid { display: flex; justify-content: space-around; font-weight: bold; }
</style>

<div class="hero">
    <h1>Servicios Agroindustriales Integrados</h1>
    <p>Cotización dinámica impulsada por modelos predictivos de Inteligencia Artificial.</p>
</div>

<!-- Barra de Indicadores de Mercado -->
<div class="market-ticker">
    <small style="display:block; text-align:center; color:#555; margin-bottom:8px;">
        📊 REFERENCIAS DE MERCADO INTERNACIONAL (Último Cierre)
    </small>
    <div class="ticker-grid">
        <span>⛽ Diésel: $<?= $last_record['diesel_usd_l'] ?> / L</span>
        <span>☕ Café Arábica: $<?= $last_record['cafe_usd_qq'] ?> / QQ</span>
        <span>🥑 Aguacate Hass: $<?= $last_record['aguacate_usd_kg'] ?> / Kg</span>
        <span>⚡ Energía US: $<?= $last_record['elec_us_kwh'] ?> / kWh</span>
    </div>
</div>

<!-- Tarjetas de Acceso a Servicios -->
<div class="grid-services">
    <div class="card">
        <h3>🌱 Procesamiento de Café</h3>
        <p>Servicios de secado rotativo, despulpado y tostado industrial calibrados por densidad de lote.</p>
        <a href="c1.php" class="card-btn">Cotizar Café</a>
    </div>

    <div class="card">
        <h3>🥑 Cadena de Frío Aguacate</h3>
        <p>Cúpula de frío, pre-enfriamiento y empaque clasificado para extensión de vida útil comercial.</p>
        <a href="a1.php" class="card-btn">Cotizar Aguacate</a>
    </div>

    <div class="card">
        <h3>🚜 Alquiler de Maquinaria</h3>
        <p>Suministro de plantas eléctricas auxiliares diésel y tractores para faena continua en finca.</p>
        <a href="m1.php" class="card-btn">Cotizar Maquinaria</a>
    </div>
</div>

<?php include 'includes/footer.php'; ?>