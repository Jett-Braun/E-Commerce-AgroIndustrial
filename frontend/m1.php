<?php
include 'includes/header.php';

$quote = null;
$error = null;

// URL apuntando a la API M1
$api_url = getenv('API_M1_URL') ?: 'http://localhost:8003';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Payload con los nombres exactos que espera el modelo Pydantic de M1
    $payload = json_encode([
        'equipment_type' => (int)$_POST['equipment_type'],
        'hours_requested' => (float)$_POST['hours_requested'],
        'fuel_cost_per_liter' => (float)$_POST['fuel_cost_per_liter']
    ]);

    $url = $api_url . '/api/maquinaria/quote';

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    if (curl_errno($ch)) {
        $error = 'Error de conexión con la API de Maquinaria: ' . curl_error($ch);
    } elseif ($http_code !== 200) {
        $error = "La API devolvió HTTP $http_code. Respuesta: " . htmlspecialchars($response);
    } else {
        $quote = json_decode($response, true);
    }
    curl_close($ch);
}
?>

<h3>🚜 Alquiler de Maquinaria y Equipos Agrícolas</h3>

<form method="POST">
    <label for="equipment_type">Tipo de Maquinaria:</label>
    <select name="equipment_type" id="equipment_type">
        <option value="1" <?= (($_POST['equipment_type'] ?? '') == '1') ? 'selected' : '' ?>>Tractor de Oruga / Mantenimiento</option>
        <option value="2" <?= (($_POST['equipment_type'] ?? '') == '2') ? 'selected' : '' ?>>Generador Diésel / Planta Eléctrica</option>
        <option value="3" <?= (($_POST['equipment_type'] ?? '') == '3') ? 'selected' : '' ?>>Camión de Carga Pesada (6x6)</option>
    </select>

    <label for="hours_requested">Horas de Operación Requeridas:</label>
    <input type="number" step="0.5" name="hours_requested" id="hours_requested" 
           value="<?= htmlspecialchars($_POST['hours_requested'] ?? '8.0') ?>" required>

    <label for="fuel_cost_per_liter">Costo de Diésel (USD / Litro):</label>
    <input type="number" step="0.01" name="fuel_cost_per_liter" id="fuel_cost_per_liter" 
           value="<?= htmlspecialchars($_POST['fuel_cost_per_liter'] ?? '0.80') ?>" required>

    <button type="submit">Calcular Tarifa con IA (M1)</button>
</form>

<?php if ($quote): ?>
    <div class="result-box">
        <h4>Cotización de Maquinaria (#<?= htmlspecialchars($quote['quote_id'] ?? 'N/A') ?>)</h4>
        <p>Costo por Hora: <strong>$<?= number_format($quote['hourly_rate_usd'] ?? 0, 2) ?> USD</strong></p>
        <p>Total Estimado (<?= htmlspecialchars($quote['hours'] ?? '0') ?> hrs): <strong>$<?= number_format($quote['total_usd'] ?? 0, 2) ?> USD</strong></p>
    </div>
<?php elseif ($error): ?>
    <div class="error-box" style="color: red; padding: 10px; border: 1px solid red; margin-top: 10px;"><?= $error ?></div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>