document.addEventListener('DOMContentLoaded', function () {
    const testResultsDiv = document.getElementById('test-results');
    const testSummaryDiv = document.getElementById('test-summary');
    let testsPassed = 0;
    let testsFailed = 0;
    const TOLERANCE = 0.015; // Adjusted tolerance for currency comparisons

    function runTest(testName, actual, expected, isNumeric = true) {
        const p = document.createElement('p');
        p.className = 'test-result';
        let pass = false;

        if (isNumeric) {
            if (actual === Infinity && expected === Infinity) {
                pass = true;
            } else if (Math.abs(actual - expected) < TOLERANCE) {
                pass = true;
            }
        } else {
            // For non-numeric, like 'N/A' or string comparison
            pass = (actual === expected);
        }

        if (pass) {
            testsPassed++;
            p.classList.add('pass');
            p.textContent = `PASS - ${testName}: Expected ${expected}, Got ${actual}`;
        } else {
            testsFailed++;
            p.classList.add('fail');
            p.textContent = `FAIL - ${testName}: Expected ${expected}, Got ${actual}`;
        }
        testResultsDiv.appendChild(p);
        updateSummary();
    }

    function updateSummary() {
        testSummaryDiv.textContent = `Tests completed: ${testsPassed} passed, ${testsFailed} failed.`;
    }

    function testCalculateMonthlyPaymentSuite() {
        console.log("Running testCalculateMonthlyPaymentSuite...");
        // Test 1: Standard calculation
        // P=$100,000, R=5%, T=360 months. Expected: 536.82 (approx)
        runTest("Monthly Payment - Standard", calculateMonthlyPayment(100000, 5, 360), 536.82);

        // Test 2: Zero interest rate
        // P=$100,000, R=0%, T=240 months. Expected: 100000 / 240 = 416.67
        runTest("Monthly Payment - Zero Interest", calculateMonthlyPayment(100000, 0, 240), 416.67);

        // Test 3: Zero principal
        // P=$0, R=5%, T=360 months. Expected: 0
        runTest("Monthly Payment - Zero Principal", calculateMonthlyPayment(0, 5, 360), 0);

        // Test 4: Zero term (P=$100,000, R=5%, T=0 months)
        // Expected: Infinity (as P > 0)
        runTest("Monthly Payment - Zero Term, P > 0", calculateMonthlyPayment(100000, 5, 0), Infinity);
        
        // Test 5: Zero term, Zero Principal (P=$0, R=5%, T=0 months)
        // Expected: 0 (as P = 0)
        runTest("Monthly Payment - Zero Term, P = 0", calculateMonthlyPayment(0, 5, 0), 0);
        console.log("testCalculateMonthlyPaymentSuite completed.");
    }

    function testEndToEndScenariosSuite() {
        console.log("Running testEndToEndScenariosSuite...");

        // Scenario 1: Original Example (Down Payment $20k)
        let inputs1 = {
            buyPurchasePrice: 200000, buyDownPayment: 20000, buyLoanTerm: 240, buyInterestRate: 0,
            sellSellingPrice: 220000, sellDownPayment: 20000, sellLoanTerm: 240, sellInterestRate: 12
        };
        let results1 = calculateAllResults(inputs1);
        runTest("E2E S1 - Buy Monthly Payment", results1.buyMonthlyPayment, 750.00); // 180000 / 240
        runTest("E2E S1 - Sell Monthly Payment", results1.sellMonthlyPayment, 2202.17); // P=200k, R=12%, T=240
        runTest("E2E S1 - Net Initial Investment", results1.netInitialInvestment, 0.00);
        runTest("E2E S1 - Monthly Cashflow", results1.monthlyCashflow, 1452.17); // 2202.17 - 750
        runTest("E2E S1 - Buy Total Principal", results1.buyTotalPrincipalPaid, 180000.00);
        runTest("E2E S1 - Buy Total Interest", results1.buyTotalInterestPaid, 0.00);
        runTest("E2E S1 - Sell Total Principal", results1.sellTotalPrincipalReceived, 200000.00);
        // Sell Total Interest: (2202.17 * 240) - 200000 = 528520.8 - 200000 = 328520.8
        runTest("E2E S1 - Sell Total Interest", results1.sellTotalInterestReceived, 328520.80);
        // Total Cashflow Over Term: (2202.17 * 240) - (750 * min(240,240)) = 528520.8 - 180000 = 348520.8
        runTest("E2E S1 - Total Cashflow Over Term", results1.totalCashflowOverTerm, 348520.80);


        // Scenario 1.2: Original Example (Down Payment $30k on Sell Side)
        let inputs1_2 = {
            buyPurchasePrice: 200000, buyDownPayment: 20000, buyLoanTerm: 240, buyInterestRate: 0,
            sellSellingPrice: 220000, sellDownPayment: 30000, sellLoanTerm: 240, sellInterestRate: 12
        };
        let results1_2 = calculateAllResults(inputs1_2);
        runTest("E2E S1.2 - Buy Monthly Payment", results1_2.buyMonthlyPayment, 750.00);
        // Sell Loan: 220k - 30k = 190k. P=190k, R=12%, T=240. Expected: 2092.06
        runTest("E2E S1.2 - Sell Monthly Payment", results1_2.sellMonthlyPayment, 2092.06);
        runTest("E2E S1.2 - Net Initial Investment", results1_2.netInitialInvestment, -10000.00); // 20k - 30k
        runTest("E2E S1.2 - Monthly Cashflow", results1_2.monthlyCashflow, 1342.06); // 2092.06 - 750
        // Total Cashflow Over Term: (2092.06 * 240) - (750 * 240) = 502094.4 - 180000 = 322094.4
        runTest("E2E S1.2 - Total Cashflow Over Term", results1_2.totalCashflowOverTerm, 322094.40);


        // Scenario 2: Sell for less example
        let inputs2 = {
            buyPurchasePrice: 200000, buyDownPayment: 20000, buyLoanTerm: 240, buyInterestRate: 0,
            sellSellingPrice: 180000, sellDownPayment: 20000, sellLoanTerm: 240, sellInterestRate: 12
        };
        let results2 = calculateAllResults(inputs2);
        runTest("E2E S2 - Buy Monthly Payment", results2.buyMonthlyPayment, 750.00);
        // Sell Loan: 180k - 20k = 160k. P=160k, R=12%, T=240. Expected: 1761.74
        runTest("E2E S2 - Sell Monthly Payment", results2.sellMonthlyPayment, 1761.74);
        runTest("E2E S2 - Net Initial Investment", results2.netInitialInvestment, 0.00);
        runTest("E2E S2 - Monthly Cashflow", results2.monthlyCashflow, 1011.74); // 1761.74 - 750
        // Total Cashflow Over Term: (1761.74 * 240) - (750 * 240) = 422817.6 - 180000 = 242817.6
        runTest("E2E S2 - Total Cashflow Over Term", results2.totalCashflowOverTerm, 242817.60);

        console.log("testEndToEndScenariosSuite completed.");
    }

    // Run all test suites
    testCalculateMonthlyPaymentSuite();
    testEndToEndScenariosSuite();
    updateSummary(); // Final update after all tests run
});
