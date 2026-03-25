<?php
/**
 * PAD Daily Files Export — SAI Recovery
 * 
 * Retrieves files delivered today from the PAD database
 * and exports them as a downloadable CSV.
 * 
 * SETUP REQUIRED:
 *   1. Fill in DB credentials below (get from Danny Lopez)
 *   2. Confirm table name and column names with Mark/Danny
 *   3. For production: move credentials to environment variables
 *   4. HIPAA: Ensure BAA is in place if exporting PHI
 * 
 * Usage:
 *   Browser: Navigate to this script's URL → triggers CSV download
 *   CLI:     php pad_daily_files_export.php
 */

// ============================================================
// CONFIG — REPLACE THESE VALUES
// ============================================================
$config = [
    'driver'   => 'mysql',              // REPLACE: 'mysql', 'sqlsrv', or 'pgsql'
    'host'     => 'localhost',           // REPLACE: PAD database host
    'port'     => '3306',               // REPLACE: 3306 (MySQL), 1433 (SQL Server), 5432 (Postgres)
    'dbname'   => 'pad_database',       // REPLACE: actual PAD database name
    'username' => 'reporting_user',     // REPLACE: read-only reporting user
    'password' => '',                   // REPLACE: reporting user password
];

// REPLACE: Actual table and column names from PAD schema
$table_name    = 'files';              // REPLACE: e.g., 'delivered_files', 'cases', etc.
$date_column   = 'delivered_date';     // REPLACE: column that tracks delivery date
$export_columns = [                    // REPLACE: columns you want in the CSV export
    'file_id',
    'patient_name',
    'carrier',
    'provider',
    'billed_amount',
    'delivered_date',
    'status',
];

// ============================================================
// DATABASE CONNECTION
// ============================================================
try {
    switch ($config['driver']) {
        case 'sqlsrv':
            $dsn = "sqlsrv:Server={$config['host']},{$config['port']};Database={$config['dbname']}";
            break;
        case 'pgsql':
            $dsn = "pgsql:host={$config['host']};port={$config['port']};dbname={$config['dbname']}";
            break;
        case 'mysql':
        default:
            $dsn = "mysql:host={$config['host']};port={$config['port']};dbname={$config['dbname']};charset=utf8mb4";
            break;
    }

    $pdo = new PDO($dsn, $config['username'], $config['password'], [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    die("Database connection failed: " . $e->getMessage());
}

// ============================================================
// QUERY — Files delivered today
// ============================================================
$today = date('Y-m-d');
$columns_sql = implode(', ', array_map(function ($col) {
    return "`$col`";  // Note: use double-quotes for SQL Server/Postgres if needed
}, $export_columns));

$sql = "SELECT {$columns_sql} FROM `{$table_name}` WHERE DATE(`{$date_column}`) = :today ORDER BY `{$date_column}` DESC";

try {
    $stmt = $pdo->prepare($sql);
    $stmt->execute(['today' => $today]);
    $rows = $stmt->fetchAll();
} catch (PDOException $e) {
    http_response_code(500);
    die("Query failed: " . $e->getMessage());
}

// ============================================================
// DETECT: Browser vs CLI
// ============================================================
$is_cli = (php_sapi_name() === 'cli');

if ($is_cli) {
    // --- CLI Output ---
    $count = count($rows);
    echo "=== PAD Daily Files Export ===\n";
    echo "Date: {$today}\n";
    echo "Files delivered today: {$count}\n\n";

    if ($count === 0) {
        echo "No files delivered today.\n";
        exit(0);
    }

    // Print header
    echo implode(' | ', $export_columns) . "\n";
    echo str_repeat('-', 80) . "\n";

    foreach ($rows as $row) {
        $values = [];
        foreach ($export_columns as $col) {
            $values[] = $row[$col] ?? '';
        }
        echo implode(' | ', $values) . "\n";
    }
    exit(0);
}

// ============================================================
// BROWSER: CSV Download
// ============================================================
if (count($rows) === 0) {
    http_response_code(200);
    header('Content-Type: text/html; charset=utf-8');
    echo "<h2>No files delivered today ({$today})</h2>";
    echo "<p>There are 0 files with a delivery date of today in the PAD database.</p>";
    echo "<p><a href='javascript:history.back()'>← Go back</a></p>";
    exit(0);
}

$filename = "pad_files_delivered_{$today}.csv";

// Headers for CSV download
header('Content-Type: text/csv; charset=utf-8');
header("Content-Disposition: attachment; filename=\"{$filename}\"");
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

// Open output stream
$output = fopen('php://output', 'w');

// UTF-8 BOM for Excel compatibility
fprintf($output, chr(0xEF) . chr(0xBB) . chr(0xBF));

// Write header row
fputcsv($output, $export_columns);

// Write data rows
foreach ($rows as $row) {
    $csv_row = [];
    foreach ($export_columns as $col) {
        $csv_row[] = $row[$col] ?? '';
    }
    fputcsv($output, $csv_row);
}

fclose($output);
exit(0);
