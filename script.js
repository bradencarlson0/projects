// Function to calculate monthly payment (now in global scope for testability)
function calculateMonthlyPayment(principal, annualInterestRate, loanTermMonths) {
    // Ensure principal is not negative; if less than or zero, treat as zero for calculation.
    if (principal <= 0) {
        return 0;
    }

    // If loan term is zero or negative
    if (loanTermMonths <= 0) {
        // If there's principal but no term (or negative term), payment is effectively infinite.
        // If principal was already zero (handled above), payment is zero.
        return Infinity;
    }

    // If annual interest rate is zero
    if (annualInterestRate === 0) {
        // Payment is simply principal divided by term.
        // loanTermMonths is guaranteed to be > 0 here.
        return parseFloat((principal / loanTermMonths).toFixed(2));
    }

    // Convert annual percentage rate to monthly decimal rate
    const monthlyInterestRate = annualInterestRate / 100 / 12;
    const n = loanTermMonths; // Number of payments
    const P = principal;    // Principal loan amount

    // Standard mortgage payment formula: M = P * [i * (1 + i)^n] / [(1 + i)^n - 1]
    const M = P * (monthlyInterestRate * Math.pow(1 + monthlyInterestRate, n)) / (Math.pow(1 + monthlyInterestRate, n) - 1);

    // Check for non-finite results (NaN, Infinity) which can happen with extreme values
    if (!isFinite(M)) {
        return Infinity; // Or handle as an error/specific value
    }

    return parseFloat(M.toFixed(2));
}

// Core calculation logic extracted for testability
function calculateAllResults(inputs) {
    const {
        buyPurchasePrice, buyDownPayment, buyLoanTerm, buyInterestRate,
        sellSellingPrice, sellDownPayment, sellLoanTerm, sellInterestRate
    } = inputs;

    // Buy Side
    const buyLoanAmount = buyPurchasePrice - buyDownPayment;
    const buyMonthlyPayment = calculateMonthlyPayment(buyLoanAmount, buyInterestRate, buyLoanTerm);

    // Sell Side
    const sellLoanAmount = sellSellingPrice - sellDownPayment;
    const sellMonthlyPayment = calculateMonthlyPayment(sellLoanAmount, sellInterestRate, sellLoanTerm);

    // Overall Metrics
    const netInitialInvestment = buyDownPayment - sellDownPayment;
    const monthlyCashflow = (isFinite(sellMonthlyPayment) ? sellMonthlyPayment : 0) - (isFinite(buyMonthlyPayment) ? buyMonthlyPayment : 0);

    // Detailed Financial Calculations
    let buyTotalPrincipalPaid = 0;
    let buyTotalInterestPaid = 0;
    let displayBuyTotalsAsNA = false;

    if (buyLoanAmount <= 0) {
        buyTotalPrincipalPaid = 0;
        buyTotalInterestPaid = 0;
    } else if (!isFinite(buyMonthlyPayment)) {
        displayBuyTotalsAsNA = true;
    } else if (buyLoanTerm === 0) {
        buyTotalPrincipalPaid = buyLoanAmount;
        buyTotalInterestPaid = 0;
    } else {
        const totalBuyPayments = buyMonthlyPayment * buyLoanTerm;
        buyTotalInterestPaid = totalBuyPayments - buyLoanAmount;
        buyTotalPrincipalPaid = buyLoanAmount;
        if (buyTotalInterestPaid < 0) buyTotalInterestPaid = 0;
    }

    let sellTotalPrincipalReceived = 0;
    let sellTotalInterestReceived = 0;
    let displaySellTotalsAsNA = false;

    if (sellLoanAmount <= 0) {
        sellTotalPrincipalReceived = 0;
        sellTotalInterestReceived = 0;
    } else if (!isFinite(sellMonthlyPayment)) {
        displaySellTotalsAsNA = true;
    } else if (sellLoanTerm === 0) {
        sellTotalPrincipalReceived = sellLoanAmount;
        sellTotalInterestReceived = 0;
    } else {
        const totalSellPayments = sellMonthlyPayment * sellLoanTerm;
        sellTotalInterestReceived = totalSellPayments - sellLoanAmount;
        sellTotalPrincipalReceived = sellLoanAmount;
        if (sellTotalInterestReceived < 0) sellTotalInterestReceived = 0;
    }

    let totalCashflowOverTerm = 0;
    let sellContribution = 0;
    if (isFinite(sellMonthlyPayment) && sellLoanTerm > 0) {
        sellContribution = sellMonthlyPayment * sellLoanTerm;
    }
    let buyContribution = 0;
    if (isFinite(buyMonthlyPayment) && buyLoanTerm > 0) {
        buyContribution = buyMonthlyPayment * Math.min(buyLoanTerm, sellLoanTerm);
    }
    totalCashflowOverTerm = sellContribution - buyContribution;
    
    let displayTotalCashflowAsNA = false;
    if (sellLoanTerm > 0 && !isFinite(sellMonthlyPayment)) displayTotalCashflowAsNA = true;
    if (Math.min(buyLoanTerm, sellLoanTerm) > 0 && !isFinite(buyMonthlyPayment)) displayTotalCashflowAsNA = true;


    return {
        buyMonthlyPayment,
        sellMonthlyPayment,
        netInitialInvestment,
        monthlyCashflow,
        buyTotalPrincipalPaid,
        buyTotalInterestPaid,
        displayBuyTotalsAsNA,
        sellTotalPrincipalReceived,
        sellTotalInterestReceived,
        displaySellTotalsAsNA,
        totalCashflowOverTerm,
        displayTotalCashflowAsNA
    };
}

document.addEventListener('DOMContentLoaded', function () {
    // Get DOM elements
    // Inputs
    const buyPurchasePriceEl = document.getElementById('buy-purchase-price');
    const buyDownPaymentEl = document.getElementById('buy-down-payment');
    const buyLoanTermEl = document.getElementById('buy-loan-term');
    const buyInterestRateEl = document.getElementById('buy-interest-rate');

    const sellSellingPriceEl = document.getElementById('sell-selling-price');
    const sellDownPaymentEl = document.getElementById('sell-down-payment');
    const sellLoanTermEl = document.getElementById('sell-loan-term');
    const sellInterestRateEl = document.getElementById('sell-interest-rate');

    // Results
    const resultBuyMonthlyPaymentEl = document.getElementById('result-buy-monthly-payment');
    const resultSellMonthlyPaymentEl = document.getElementById('result-sell-monthly-payment');
    const resultNetInitialInvestmentEl = document.getElementById('result-net-initial-investment');
    const resultMonthlyCashflowEl = document.getElementById('result-monthly-cashflow');

    // New Detailed Result Elements
    const buyTotalPrincipalEl = document.getElementById('buy-total-principal');
    const buyTotalInterestEl = document.getElementById('buy-total-interest');
    const sellTotalPrincipalEl = document.getElementById('sell-total-principal');
    const sellTotalInterestEl = document.getElementById('sell-total-interest');
    const totalCashflowOverTermEl = document.getElementById('total-cashflow-over-term');


    // Calculate button
    const calculateButton = document.getElementById('calculate-button');

    if (calculateButton) {
        calculateButton.addEventListener('click', function () {
            // Get Buy Side values
            const buyPurchasePrice = parseFloat(buyPurchasePriceEl.value) || 0;
            const buyDownPayment = parseFloat(buyDownPaymentEl.value) || 0;
            const buyLoanTerm = parseInt(buyLoanTermEl.value) || 0;
            const buyInterestRate = parseFloat(buyInterestRateEl.value) || 0;

            // Get Sell Side values
            const sellSellingPrice = parseFloat(sellSellingPriceEl.value) || 0;
            const sellDownPayment = parseFloat(sellDownPaymentEl.value) || 0;
            const sellLoanTerm = parseInt(sellLoanTermEl.value) || 0;
            const sellInterestRate = parseFloat(sellInterestRateEl.value) || 0;

            const inputs = {
                buyPurchasePrice, buyDownPayment, buyLoanTerm, buyInterestRate,
                sellSellingPrice, sellDownPayment, sellLoanTerm, sellInterestRate
            };

            const results = calculateAllResults(inputs);

            // --- Display Results ---
            resultBuyMonthlyPaymentEl.textContent = isFinite(results.buyMonthlyPayment) ? `$${results.buyMonthlyPayment.toFixed(2)}` : 'N/A';
            resultSellMonthlyPaymentEl.textContent = isFinite(results.sellMonthlyPayment) ? `$${results.sellMonthlyPayment.toFixed(2)}` : 'N/A';
            resultNetInitialInvestmentEl.textContent = `$${results.netInitialInvestment.toFixed(2)}`;
            resultMonthlyCashflowEl.textContent = `$${results.monthlyCashflow.toFixed(2)}`;

            buyTotalPrincipalEl.textContent = results.displayBuyTotalsAsNA ? 'N/A' : `$${results.buyTotalPrincipalPaid.toFixed(2)}`;
            buyTotalInterestEl.textContent = results.displayBuyTotalsAsNA ? 'N/A' : `$${results.buyTotalInterestPaid.toFixed(2)}`;

            sellTotalPrincipalEl.textContent = results.displaySellTotalsAsNA ? 'N/A' : `$${results.sellTotalPrincipalReceived.toFixed(2)}`;
            sellTotalInterestEl.textContent = results.displaySellTotalsAsNA ? 'N/A' : `$${results.sellTotalInterestReceived.toFixed(2)}`;
            
            totalCashflowOverTermEl.textContent = results.displayTotalCashflowAsNA ? 'N/A' :`$${results.totalCashflowOverTerm.toFixed(2)}`;

            // Handle Infinite Return message styling via CSS class
            resultNetInitialInvestmentEl.classList.remove('infinite-return-positive');
            if (results.netInitialInvestment <= 0 && results.monthlyCashflow > 0) {
                 resultNetInitialInvestmentEl.classList.add('infinite-return-positive');
            }

            // Optional: Basic validation logging (can be expanded to UI messages)
            // These checks could also be part of calculateAllResults if they influence output data
            const buyLoanAmount = buyPurchasePrice - buyDownPayment; // Recalculate for logging, or pass from results
            if (buyLoanAmount < 0) {
                console.warn("Buy side: Down payment is greater than purchase price.");
            }
            const sellLoanAmount = sellSellingPrice - sellDownPayment; // Recalculate for logging
            if (sellLoanAmount < 0) {
                console.warn("Sell side: Down payment received is greater than selling price.");
            }
        });
    } else {
        // Ensure this error is meaningful in test.html context too
        const testResultsDiv = document.getElementById('test-results');
        if (testResultsDiv) {
            const p = document.createElement('p');
            p.className = 'fail';
            p.textContent = 'CRITICAL: Calculate button not found. End-to-end tests cannot run.';
            testResultsDiv.appendChild(p);
        } else {
            console.error("Calculate button with ID 'calculate-button' not found!");
        }
    }
});
