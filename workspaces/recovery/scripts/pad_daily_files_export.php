<?php
/**
 * PAD Daily Files Export — SAI Recovery
 * 
 * Retrieves files delivered today from the PAD database
 * and exports them as a CSV download to the browser.
 * 
 * REQUIREMENTS:
 *   - Update DB credentials below (get from Danny Lopez / Mark Winters)
 *   - Update table/column names to match actual PAD schema
 *   - Ensure HIPAA BAA compliance is confirmed before connecting to PHI
 * 
 * USAGE:
 *   Access via browser: https://your-server.com/pad_daily_files_export.php
 *   Or CLI: php pad_daily_files_export.php (outputs CSV to stdout)
 */

// ============================================================
// CONFIGURATION — UPDATE THESE VALUES
// ============================================================

// Database connection (get actual values from Danny/Mark)
$db_config = [
    'host'     => '60.60.60.200',       // PAD server IP (confirmed from entry bot)
    'port'     => '3306',               // Default MySQL port — change if SQL Server (1433) or PostgreSQL (5432)
    'dbname'   => 'pad_database',       // REPLACE with actual database name
    'username' => 'reporting_user',     // REPLACE — do NOT use 'thebot' for reporting
    'password' => '',                   // REPLACE — use env variable in production
    'driver'   => 'mysql',             // Options: 'mysql', 'sqlsrv', 'pgsql'
];

// Query configuration — UPDATE table/column names to match PAD schema
$table_name       = 'cases';           // REPLACE with actual table name
$date_column      = 'delivered_date';  // REPLACE with the column that tracks delivery date
$status_column    = 'status';          // REPLACE if there's a delivery status field
$delivered_status = 'delivered';       // REPLACE with the actual status value for "delivered"

// Columns to export — UPDATE to match actual PAD columns
$export_columns = [
    'id',
    'account_no',
    'claim_number',
    'patient_fname',
    'patient_lname',
    'insurance_name',
    'provider_name',
    'facility_name',
    'delivered_date',
    'status',
    'total_billed',
    'total_paid',
];

// ============================================================
// DATABASE CONNECTION
// ============================================================

function getConnection(array $config): PDO {
    switch ($config['driver']) {
        case 'mysql':
            $dsn = "mysql:host={$config['host']};port={$config['port']};dbname={$config['dbname']};charset=utf8mb4";
            break;
        case 'sqlsrv':
            $dsn = "sqlsrv:Server={$config['host']},{$config['port']};Database={$config['dbname']}";
            break;
        case 'pgsql':
            $dsn = "pgsql:host={$config['host']};port={$config['port']};dbname={$config['dbname']}";
            break;
        default:
            die("Unsupported database driver: {$config['driver']}");
    }

    try {
        $pdo = new PDO($dsn, $config['username'], $config['password'], [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ]);
        return $pdo;
    } catch (PDOException $e) {
        die("Database connection failed: " . $e->getMessage());
    }
}

// ============================================================
// QUERY — FILES DELIVERED TODAY
// ============================================================

function getFilesDeliveredToday(PDO $pdo, string $table, string $dateCol, string $statusCol, string $statusVal, array $columns): array {
    $today = date('Y-m-d');
    $colList = implode(', ', array_map(function($col) {
        // Basic sanitization — column names should be whitelisted
        return preg_replace('/[^a-zA-Z0-9_]/', '', $col);
    }, $columns));

    // Use parameterized query for the date value
    $sql = "SELECT {$colList} 
            FROM {$table} 
            WHERE DATE({$dateCol}) = :today";
    
    // Optionally filter by status — uncomment if needed:
    // $sql .= " AND {$statusCol} = :status";

    $stmt = $pdo->prepare($sql);
    $stmt->bindParam(':today', $today, PDO::PARAM_STR);
    // $stmt->bindParam(':status', $statusVal, PDO::PARAM_STR);
    
    $stmt->execute();
    return $stmt->fetchAll();
}

// ============================================================
// CSV EXPORT TO BROWSER
// ============================================================

function exportToCsv(array $rows, array $headers, string $filename): void {
    // Set headers for browser download
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $filename . '"');
    header('Cache-Control: no-cache, no-store, must-revalidate');
    header('Pragma: no-cache');
    header('Expires: 0');

    $output = fopen('php://output', 'w');

    // Write UTF-8 BOM for Excel compatibility
    fprintf($output, chr(0xEF) . chr(0xBB) . chr(0xBF));

    // Write header row
    fputcsv($output, $headers);

    // Write data rows
    foreach ($rows as $row) {
        fputcsv($output, $row);
    }

    fclose($output);
}

// ============================================================
// MAIN EXECUTION
// ============================================================

try {
    $pdo  = getConnection($db_config);
    $rows = getFilesDeliveredToday(
        $pdo, 
        $table_name, 
        $date_column, 
        $status_column, 
        $delivered_status, 
        $export_columns
    );

    $today    = date('Y-m-d');
    $filename = "pad_files_delivered_{$today}.csv";
    $count    = count($rows);

    // If called from CLI, show summary first
    if (php_sapi_name() === 'cli') {
        echo "=== PAD Daily Files Export ===" . PHP_EOL;
        echo "Date: {$today}" . PHP_EOL;
        echo "Files delivered today: {$count}" . PHP_EOL;
        echo "---" . PHP_EOL;

        if ($count === 0) {
            echo "No files delivered today." . PHP_EOL;
            exit(0);
        }

        // In CLI mode, output CSV to stdout
        $output = fopen('php://stdout', 'w');
        fputcsv($output, $export_columns);
        foreach ($rows as $row) {
            fputcsv($output, $row);
        }
        fclose($output);
    } else {
        // Browser mode — trigger download
        if ($count === 0) {
            // Show a simple message instead of empty CSV
            header('Content-Type: text/html; charset=utf-8');
            echo "<!DOCTYPE html><html><body>";
            echo "<h2>PAD Daily Files Export — {$today}</h2>";
            echo "<p>No files were delivered today (0 records found).</p>";
            echo "<p><a href='javascript:history.back()'>Go Back</a></p>";
            echo "</body></html>";
            exit;
        }

        exportToCsv($rows, $export_columns, $filename);
    }

} catch (Exception $e) {
    if (php_sapi_name() === 'cli') {
        echo "ERROR: " . $e->getMessage() . PHP_EOL;
        exit(1);
    } else {
        header('Content-Type: text/html; charset=utf-8');
        http_response_code(500);
        echo "<!DOCTYPE html><html><body>";
        echo "<h2>Export Error</h2>";
        echo "<p>An error occurred while generating the export. Please contact Mark Winters or IT support.</p>";
        // Don't expose error details in browser for security
        echo "</body></html>";
        error_log("PAD Export Error: " . $e->getMessage());
    }
}
