<?php
define('DB_HOST', getenv('DB_HOST') ?: 'bxcyjzl01ttmj7sbirum-mysql.services.clever-cloud.com');
define('DB_USER', getenv('DB_USER') ?: 'uxefqjn8zmichsb1');
define('DB_PASS', getenv('DB_PASS') ?: 'NEm0EL1wZzMX0LPNjMQA');
define('DB_NAME', getenv('DB_NAME') ?: 'bxcyjzl01ttmj7sbirum');
define('DB_PORT', getenv('DB_PORT') ?: '3306');

// Endpoints de Microservicios en Render apuntando a sus servicios reales
define('API_C1_URL', 'https://c1-78vn.onrender.com'); // Apunta a c1.py (/api/cafe/quote)
define('API_A1_URL', 'https://m1-g3qf.onrender.com'); // Apunta a m1.py (/api/maquinaria/quote)
define('API_M1_URL', 'https://a1-y28x.onrender.com'); // Apunta a a1.py (/api/aguacate/quote)
?>