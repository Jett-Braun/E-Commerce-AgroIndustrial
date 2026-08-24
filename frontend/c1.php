<?php
include 'includes/header.php';

$quote = null;
$error = null;
$default_fuel = "0.80";

// 🔥 OBTENER URL DESDE VARIABLES DE ENTORNO
$api_url = getenv('API_C1_URL');
if (!$api_url) {
    // Fallback para desarrollo local
    $api_url = 'http://localhost:8001';
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $payload = json_encode([
        'service_id' => (int)$_POST['service_id'],
        'batch_volume_qq' => (float)$_POST['batch_volume_qq'],
        'fuel_cost_per_liter' => (float)$_POST['fuel_cost_per_liter']
    ]);

    $url = $api_url . '/api/cafe/quote';

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    if (curl_errno($ch)) {
        $error = 'Error de conexión con la API de Café (C1): ' . curl_error($ch);
    } elseif ($http_code !== 200) {
        $error = "La API de Café devolvió un error: HTTP $http_code. Respuesta: " . htmlspecialchars($response);
    } else {
        $quote = json_decode($response, true);
    }
    curl_close($ch);
}
?>

<h3>🌱 Cotizador de Procesamiento de Café</h3>

<form method="POST">
    <label for="service_id">Servicio Requerido:</label>
    <select name="service_id" id="service_id">
        <option value="1" <?= (($_POST['service_id'] ?? '') == '1') ? 'selected' : '' ?>>Secado Mecánico Rotativo</option>
        <option value="2" <?= (($_POST['service_id'] ?? '') == '2') ? 'selected' : '' ?>>Despulpado y Lavado</option>
        <option value="3" <?= (($_POST['service_id'] ?? '') == '3') ? 'selected' : '' ?>>Tostado Industrial</option>
    </select>

    <label for="batch_volume_qq">Volumen del Lote (Quintales - QQ):</label>
    <input type="number" step="0.1" name="batch_volume_qq" id="batch_volume_qq" 
           value="<?= htmlspecialchars($_POST['batch_volume_qq'] ?? '50.0') ?>" required>

    <label for="fuel_cost_per_liter">Costo del Diésel (USD / Litro):</label>
    <input type="number" step="0.01" name="fuel_cost_per_liter" id="fuel_cost_per_liter" 
           value="<?= htmlspecialchars($_POST['fuel_cost_per_liter'] ?? $default_fuel) ?>" required>

    <button type="submit">Calcular Tarifa con IA (C1)</button>
</form>

<?php if ($quote): ?>
    <div class="result-box">
        <h4>Cotización Estimada (#<?= htmlspecialchars($quote['quote_id'] ?? 'N/A') ?>)</h4>
        <p>Tarifa por Quintal: <strong>$<?= number_format($quote['unit_price_usd'] ?? 0, 2) ?> USD</strong></p>
        <p>Total Estimado (<?= htmlspecialchars($quote['volume_qq'] ?? '0') ?> QQ): <strong>$<?= number_format($quote['total_usd'] ?? 0, 2) ?> USD</strong></p>
    </div>
<?php elseif ($error): ?>
    <div class="error-box" style="color: red; padding: 10px; border: 1px solid red; margin-top: 10px;"><?= htmlspecialchars($error) ?></div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>