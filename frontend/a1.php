<?php
include 'includes/header.php';

$quote = null;
$error = null;

// URL apuntando a la API A1
$api_url = getenv('API_A1_URL') ?: 'http://localhost:8002';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Payload con los nombres exactos que espera el modelo Pydantic de A1
    $payload = json_encode([
        'service_id' => (int)$_POST['package_type'],
        'batch_weight_kg' => (float)$_POST['weight_kg'],
        'cooling_hours' => 24.0,
        'electricity_kwh_rate' => 0.15
    ]);

    $url = $api_url . '/api/aguacate/quote';

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    if (curl_errno($ch)) {
        $error = 'Error de conexión con la API de Logística/Aguacate: ' . curl_error($ch);
    } elseif ($http_code !== 200) {
        $error = "La API devolvió HTTP $http_code. Respuesta: " . htmlspecialchars($response);
    } else {
        $quote = json_decode($response, true);
    }
    curl_close($ch);
}
?>

<h3>📦 Servicio de Empaque y Logística de Carga (Aguacate)</h3>

<form method="POST">
    <label for="package_type">Tipo de Servicio:</label>
    <select name="package_type" id="package_type">
        <option value="1" <?= (($_POST['package_type'] ?? '') == '1') ? 'selected' : '' ?>>Pre-enfriado y Almacenamiento en Frío</option>
        <option value="2" <?= (($_POST['package_type'] ?? '') == '2') ? 'selected' : '' ?>>Clasificación y Empaque de Exportación</option>
    </select>

    <label for="weight_kg">Peso Total de la Carga (Kg):</label>
    <input type="number" step="1" name="weight_kg" id="weight_kg" 
           value="<?= htmlspecialchars($_POST['weight_kg'] ?? '500') ?>" required>

    <button type="submit">Calcular Tarifa</button>
</form>

<?php if ($quote): ?>
    <div class="result-box">
        <h4>Cotización de Logística (#<?= htmlspecialchars($quote['quote_id'] ?? 'N/A') ?>)</h4>
        <p>Costo por Kilogramo: <strong>$<?= number_format($quote['unit_price_per_kg_usd'] ?? 0, 3) ?> USD</strong></p>
        <p>Total Servicio: <strong>$<?= number_format($quote['total_usd'] ?? 0, 2) ?> USD</strong></p>
    </div>
<?php elseif ($error): ?>
    <div class="error-box" style="color: red; padding: 10px; border: 1px solid red; margin-top: 10px;"><?= $error ?></div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>