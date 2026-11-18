import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  CreditCard,
  Download,
  FileSpreadsheet,
  FolderKanban,
  Landmark,
  Printer,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { exportRowsToCSV, formatCurrency, formatDate } from "../utils/formatters";

// ============================================================================
// 5. SALES, CUSTOMERS, INVOICES & PAYMENTS MODULE
// ============================================================================
export const SalesAndInvoicesView: React.FC<{ initialTab?: "invoices" | "payments" | "orders" | "customers" }> = ({
  initialTab = "invoices",
}) => {
  const { user, hasPermission } = useAuth();
  const [tab, setTab] = useState(initialTab);
  const [customers, setCustomers] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);

  const [invCustId, setInvCustId] = useState("");
  const [invProdId, setInvProdId] = useState("");
  const [invQty, setInvQty] = useState("2");

  const [payInvId, setPayInvId] = useState("");
  const [payAmount, setPayAmount] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  const loadSalesData = async () => {
    try {
      const [cRes, oRes, iRes, pRes, prodRes] = await Promise.all([
        apiRequest("/customers"),
        apiRequest("/sales/orders"),
        apiRequest("/invoices"),
        apiRequest("/payments"),
        apiRequest("/inventory/products"),
      ]);
      setCustomers(cRes.items || []);
      setOrders(oRes.items || []);
      setInvoices(iRes.items || []);
      setPayments(pRes.items || []);
      setProducts(prodRes.items || []);
      if (cRes.items?.length && !invCustId) setInvCustId(cRes.items[0].id);
      if (prodRes.items?.length && !invProdId) setInvProdId(prodRes.items[8]?.id || prodRes.items[0].id);
      const unpaid = (iRes.items || []).find((x: any) => x.balance_due > 0);
      if (unpaid) {
        setPayInvId(unpaid.id);
        setPayAmount(String(unpaid.balance_due));
      }
    } catch (e: any) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    loadSalesData();
  }, [user?.organization_id]);

  const handleCreateInvoice = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      const res = await apiRequest("/invoices", {
        method: "POST",
        body: JSON.stringify({
          customer_id: invCustId,
          deduct_inventory: true,
          items: [{ product_id: invProdId, quantity: Number(invQty), tax_rate: 8.0 }],
        }),
      });
      setMsg(
        `Invoice ${res.invoice_number} issued (${formatCurrency(res.total_amount)})! Stock deducted and balanced GL Journal Entry (${res.journal_entry_id.slice(0, 8)}) posted.`
      );
      loadSalesData();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      const idemKey = `idem-${payInvId}-${payAmount}-${Date.now()}`;
      const res = await apiRequest("/payments", {
        method: "POST",
        headers: { "Idempotency-Key": idemKey },
        body: JSON.stringify({
          invoice_id: payInvId,
          amount: Number(payAmount),
          payment_method: "BANK_TRANSFER",
        }),
      });
      setMsg(
        `Payment ${res.payment_number} recorded! Invoice status: ${res.invoice_status} (Remaining Due: ${formatCurrency(res.invoice_balance_due)}).`
      );
      loadSalesData();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[#648BFF]" />
            Sales, Customer Billing, Invoices & Receipts
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Customer → Quotation → Sales Order → Stock Allocation → Tax Invoice → Idempotent Payment → GL Posting
          </p>
        </div>
        <div className="flex items-center gap-2">
          {[
            { id: "invoices", label: "Invoices" },
            { id: "payments", label: "Payments" },
            { id: "orders", label: "Sales Orders" },
            { id: "customers", label: "Customers" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium ${
                tab === t.id ? "bg-[#648BFF] text-white" : "glass-panel text-[#94A3B8]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-[#20C997]/15 border border-[#20C997]/40 text-xs text-[#20C997]">
          {msg}
        </div>
      )}
      {err && (
        <div className="p-3 rounded-xl bg-[#F06464]/15 border border-[#F06464]/40 text-xs text-[#F06464]">
          {err}
        </div>
      )}

      {tab === "invoices" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 glass-table-container rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold">Customer Tax Invoices ({invoices.length})</h2>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl glass-panel text-xs"
              >
                <Printer className="w-3.5 h-3.5" /> Print / Save PDF
              </button>
            </div>
            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-xs tabular-nums">
                <thead>
                  <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                    <th className="py-2">Invoice #</th>
                    <th className="py-2">Customer</th>
                    <th className="py-2">Issue Date</th>
                    <th className="py-2 text-right">Total (LKR)</th>
                    <th className="py-2 text-right">Paid</th>
                    <th className="py-2 text-right">Balance Due</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="border-b border-white/5">
                      <td className="py-2.5 font-mono text-[#648BFF]">{inv.invoice_number}</td>
                      <td className="py-2.5 font-medium">{inv.customer_name}</td>
                      <td className="py-2.5">{formatDate(inv.issue_date)}</td>
                      <td className="py-2.5 text-right font-semibold">
                        {formatCurrency(inv.total_amount)}
                      </td>
                      <td className="py-2.5 text-right text-[#20C997]">
                        {formatCurrency(inv.amount_paid)}
                      </td>
                      <td className="py-2.5 text-right font-bold text-[#F4B740]">
                        {formatCurrency(inv.balance_due)}
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] ${
                            inv.status === "PAID"
                              ? "bg-[#20C997]/20 text-[#20C997]"
                              : inv.status === "OVERDUE"
                              ? "bg-[#F06464]/20 text-[#F06464]"
                              : "bg-[#F4B740]/20 text-[#F4B740]"
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="lg:col-span-4 space-y-5">
            {hasPermission("invoices.create") && (
              <form onSubmit={handleCreateInvoice} className="glass-panel rounded-2xl p-5 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#648BFF]">
                  + Issue Customer Invoice (Auto-Posts GL)
                </h3>
                <select
                  value={invCustId}
                  onChange={(e) => setInvCustId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                >
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.customer_code} — {c.name}
                    </option>
                  ))}
                </select>
                <select
                  value={invProdId}
                  onChange={(e) => setInvProdId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} ({p.quantity_available} avail @ {formatCurrency(p.selling_price)})
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min="1"
                  required
                  value={invQty}
                  onChange={(e) => setInvQty(e.target.value)}
                  placeholder="Quantity"
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                />
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
                >
                  Issue Invoice & Post to Ledger
                </button>
              </form>
            )}

            {hasPermission("payments.create") && (
              <form onSubmit={handleRecordPayment} className="glass-panel rounded-2xl p-5 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#20C997]">
                  Record Customer Payment Receipt
                </h3>
                <select
                  value={payInvId}
                  onChange={(e) => {
                    setPayInvId(e.target.value);
                    const found = invoices.find((x) => x.id === e.target.value);
                    if (found) setPayAmount(String(found.balance_due));
                  }}
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                >
                  {invoices
                    .filter((x) => x.balance_due > 0)
                    .map((inv) => (
                      <option key={inv.id} value={inv.id}>
                        {inv.invoice_number} — Due: {formatCurrency(inv.balance_due)}
                      </option>
                    ))}
                </select>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value)}
                  placeholder="Payment Amount (LKR)"
                  className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                />
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-xl bg-[#20C997] text-[#080D18] text-xs font-bold"
                >
                  Record Payment & Update AR
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {tab === "payments" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Recorded Customer Receipts & Settlements ({payments.length})</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Payment #</th>
                <th className="py-2">Invoice #</th>
                <th className="py-2">Customer</th>
                <th className="py-2">Date</th>
                <th className="py-2">Method</th>
                <th className="py-2 text-right">Amount (LKR)</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#20C997]">{p.payment_number}</td>
                  <td className="py-2.5 font-mono text-[#648BFF]">{p.invoice_number}</td>
                  <td className="py-2.5 font-medium">{p.customer_name}</td>
                  <td className="py-2.5">{formatDate(p.payment_date)}</td>
                  <td className="py-2.5">{p.payment_method}</td>
                  <td className="py-2.5 text-right font-bold text-[#20C997]">
                    {formatCurrency(p.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "orders" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Confirmed Sales Orders ({orders.length})</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">SO Number</th>
                <th className="py-2">Customer</th>
                <th className="py-2">Warehouse</th>
                <th className="py-2">Order Date</th>
                <th className="py-2 text-right">Total (LKR)</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((so) => (
                <tr key={so.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#648BFF]">{so.so_number}</td>
                  <td className="py-2.5 font-medium">{so.customer_name}</td>
                  <td className="py-2.5">{so.warehouse_name}</td>
                  <td className="py-2.5">{formatDate(so.order_date)}</td>
                  <td className="py-2.5 text-right font-semibold">
                    {formatCurrency(so.total_amount)}
                  </td>
                  <td className="py-2.5">{so.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "customers" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Enterprise Customers & Receivables Aging ({customers.length})</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Code</th>
                <th className="py-2">Customer Name</th>
                <th className="py-2">Segment</th>
                <th className="py-2 text-right">Credit Limit</th>
                <th className="py-2 text-right">Outstanding Receivables</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#648BFF]">{c.customer_code}</td>
                  <td className="py-2.5 font-medium">{c.name}</td>
                  <td className="py-2.5">{c.customer_type}</td>
                  <td className="py-2.5 text-right text-[#94A3B8]">
                    {formatCurrency(c.credit_limit)}
                  </td>
                  <td className="py-2.5 text-right font-bold text-[#F4B740]">
                    {formatCurrency(c.outstanding_balance)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 6. DOUBLE-ENTRY ACCOUNTING & FINANCIAL STATEMENTS MODULE
// ============================================================================
export const FinanceAccountingView: React.FC<{
  initialTab?: "coa" | "journals" | "trial-balance" | "pnl" | "balance-sheet" | "expenses";
}> = ({ initialTab = "trial-balance" }) => {
  const { user, hasPermission } = useAuth();
  const [tab, setTab] = useState(initialTab);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [journals, setJournals] = useState<any[]>([]);
  const [trialBalance, setTrialBalance] = useState<any | null>(null);
  const [pnl, setPnl] = useState<any | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<any | null>(null);
  const [expenses, setExpenses] = useState<any[]>([]);

  // Balanced Manual Journal Form
  const [jeDesc, setJeDesc] = useState("Accrued utility & infrastructure allocation");
  const [debitCode, setDebitCode] = useState("6100");
  const [creditCode, setCreditCode] = useState("1000");
  const [jeAmount, setJeAmount] = useState("45000");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  const loadFinance = async () => {
    try {
      const [accRes, jRes, tbRes, pnlRes, bsRes, expRes] = await Promise.all([
        apiRequest("/finance/accounts"),
        apiRequest("/finance/journal-entries"),
        apiRequest("/finance/trial-balance"),
        apiRequest("/finance/profit-loss"),
        apiRequest("/finance/balance-sheet"),
        apiRequest("/finance/expenses"),
      ]);
      setAccounts(accRes.items || []);
      setJournals(jRes.items || []);
      setTrialBalance(tbRes);
      setPnl(pnlRes);
      setBalanceSheet(bsRes);
      setExpenses(expRes.items || []);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    loadFinance();
  }, [user?.organization_id]);

  const handlePostBalancedJournal = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      const amt = Number(jeAmount);
      const res = await apiRequest("/finance/journal-entries", {
        method: "POST",
        body: JSON.stringify({
          description: jeDesc,
          auto_post: true,
          lines: [
            { account_code: debitCode, debit: amt, credit: 0 },
            { account_code: creditCode, debit: 0, credit: amt },
          ],
        }),
      });
      setMsg(
        `Posted Balanced Journal Entry ${res.entry_number} (Debits = Credits = ${formatCurrency(res.total_debit)}).`
      );
      loadFinance();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const handleReverseJournal = async (entryId: string) => {
    setErr(null);
    setMsg(null);
    try {
      const res = await apiRequest(`/finance/journal-entries/${entryId}/reverse`, {
        method: "POST",
        body: JSON.stringify({ reason: "Controller reversal entry" }),
      });
      setMsg(`Posted Reversal Entry ${res.reversal_entry_number} for immutable audit trail.`);
      loadFinance();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Landmark className="w-5 h-5 text-[#648BFF]" />
            Double-Entry General Ledger & Financial Statements
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Strict Double-Entry Invariant (<code className="text-[#20C997]">Total Debits = Total Credits</code>) • Immutable Posted Journals • Reversal Auditing
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: "trial-balance", label: "Trial Balance" },
            { id: "pnl", label: "Profit & Loss" },
            { id: "balance-sheet", label: "Balance Sheet" },
            { id: "journals", label: "Journal Entries" },
            { id: "coa", label: "Chart of Accounts" },
            { id: "expenses", label: "Expenses" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium ${
                tab === t.id ? "bg-[#648BFF] text-white" : "glass-panel text-[#94A3B8]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-xl bg-[#20C997]/15 border border-[#20C997]/40 text-xs text-[#20C997]">
          {msg}
        </div>
      )}
      {err && (
        <div className="p-3 rounded-xl bg-[#F06464]/15 border border-[#F06464]/40 text-xs text-[#F06464]">
          {err}
        </div>
      )}

      {tab === "trial-balance" && trialBalance && (
        <div className="glass-table-container rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold">General Ledger Trial Balance</h2>
              <p className="text-xs text-[#94A3B8]">
                Verified from Posted Journal Lines • Status:{" "}
                <strong className={trialBalance.is_balanced ? "text-[#20C997]" : "text-[#F06464]"}>
                  {trialBalance.is_balanced ? "STRICTLY BALANCED (Debits == Credits)" : "OUT OF BALANCE"}
                </strong>
              </p>
            </div>
            <button
              onClick={() => exportRowsToCSV("nexora_trial_balance.csv", trialBalance.accounts)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl glass-panel text-xs"
            >
              <Download className="w-3.5 h-3.5" /> Export CSV
            </button>
          </div>

          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Code</th>
                <th className="py-2">Account Name</th>
                <th className="py-2">Category</th>
                <th className="py-2 text-right">Debit Balance (LKR)</th>
                <th className="py-2 text-right">Credit Balance (LKR)</th>
              </tr>
            </thead>
            <tbody>
              {(trialBalance.accounts || []).map((a: any) => (
                <tr key={a.code} className="border-b border-white/5">
                  <td className="py-2 font-mono text-[#648BFF]">{a.code}</td>
                  <td className="py-2 font-medium">{a.name}</td>
                  <td className="py-2 text-[#94A3B8]">{a.account_type}</td>
                  <td className="py-2 text-right">
                    {a.debit_balance > 0 ? formatCurrency(a.debit_balance) : "—"}
                  </td>
                  <td className="py-2 text-right">
                    {a.credit_balance > 0 ? formatCurrency(a.credit_balance) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-[#648BFF]/50 font-bold text-sm text-[#20C997]">
                <td colSpan={3} className="py-3">
                  GRAND TOTAL (DOUBLE-ENTRY VERIFIED)
                </td>
                <td className="py-3 text-right">{formatCurrency(trialBalance.total_debit)}</td>
                <td className="py-3 text-right">{formatCurrency(trialBalance.total_credit)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {tab === "pnl" && pnl && (
        <div className="glass-table-container rounded-2xl p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold">Income Statement (Statement of Profit or Loss)</h2>
            <span className="text-xs font-semibold text-[#20C997]">
              Net Margin: {pnl.net_margin_percent?.toFixed(2)}%
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 tabular-nums">
            <div className="glass-panel p-4 rounded-xl">
              <div className="text-xs text-[#94A3B8]">Total Revenue</div>
              <div className="text-lg font-bold text-[#20C997] mt-1">
                {formatCurrency(pnl.total_revenue)}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-xl">
              <div className="text-xs text-[#94A3B8]">Cost of Goods Sold (COGS)</div>
              <div className="text-lg font-bold text-[#F4B740] mt-1">
                {formatCurrency(pnl.total_cogs)}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-xl">
              <div className="text-xs text-[#94A3B8]">Operating Expenses</div>
              <div className="text-lg font-bold text-[#F06464] mt-1">
                {formatCurrency(pnl.total_operating_expenses)}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-xl border border-[#20C997]/40">
              <div className="text-xs text-[#94A3B8]">Net Profit</div>
              <div className="text-lg font-bold text-[#20C997] mt-1">
                {formatCurrency(pnl.net_profit)}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === "balance-sheet" && balanceSheet && (
        <div className="glass-table-container rounded-2xl p-6 space-y-4 tabular-nums">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold">Statement of Financial Position (Balance Sheet)</h2>
            <span className="px-3 py-1 rounded-full bg-[#20C997]/20 text-[#20C997] text-xs font-semibold">
              Assets = Liabilities + Equity ({balanceSheet.is_balanced ? "Verified" : "Check"})
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="glass-panel p-4 rounded-xl">
              <div className="text-xs text-[#94A3B8]">Total Assets</div>
              <div className="text-lg font-bold text-[#648BFF] mt-1">
                {formatCurrency(balanceSheet.total_assets)}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-xl">
              <div className="text-xs text-[#94A3B8]">Total Liabilities</div>
              <div className="text-lg font-bold text-[#F4B740] mt-1">
                {formatCurrency(balanceSheet.total_liabilities)}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-xl">
              <div className="text-xs text-[#94A3B8]">Total Equity (incl. Retained Earnings)</div>
              <div className="text-lg font-bold text-[#20C997] mt-1">
                {formatCurrency(balanceSheet.total_equity)}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === "journals" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 glass-table-container rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-bold">General Ledger Journal Entries ({journals.length})</h2>
            <div className="space-y-3 max-h-[540px] overflow-y-auto">
              {journals.map((je) => (
                <div key={je.id} className="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <div>
                      <span className="font-mono font-bold text-[#648BFF] mr-2">
                        {je.entry_number}
                      </span>
                      <span className="font-medium">{je.description}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-[#94A3B8]">{formatDate(je.entry_date)}</span>
                      <span className="px-2 py-0.5 rounded bg-[#20C997]/20 text-[#20C997] text-[10px]">
                        {je.status}
                      </span>
                      {je.status === "POSTED" && hasPermission("finance.post") && (
                        <button
                          onClick={() => handleReverseJournal(je.id)}
                          className="flex items-center gap-1 px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 text-[10px]"
                          title="Create Inverting Reversal Entry"
                        >
                          <RotateCcw className="w-3 h-3" /> Reverse
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="text-[11px] text-[#94A3B8] flex justify-between tabular-nums">
                    <span>Ref: {je.reference_type} ({je.reference_number})</span>
                    <span className="text-[#20C997] font-mono">
                      Dr: {formatCurrency(je.total_debit)} | Cr: {formatCurrency(je.total_credit)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {hasPermission("finance.manage") && (
            <form onSubmit={handlePostBalancedJournal} className="lg:col-span-4 glass-panel rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold">Post Balanced Journal Entry</h3>
              <input
                required
                value={jeDesc}
                onChange={(e) => setJeDesc(e.target.value)}
                placeholder="Journal Narrative"
                className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
              />
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-[#94A3B8]">Debit Account</label>
                  <select
                    value={debitCode}
                    onChange={(e) => setDebitCode(e.target.value)}
                    className="w-full px-2.5 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                  >
                    {accounts.map((a) => (
                      <option key={a.code} value={a.code}>
                        {a.code} — {a.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-[#94A3B8]">Credit Account</label>
                  <select
                    value={creditCode}
                    onChange={(e) => setCreditCode(e.target.value)}
                    className="w-full px-2.5 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
                  >
                    {accounts.map((a) => (
                      <option key={a.code} value={a.code}>
                        {a.code} — {a.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <input
                type="number"
                required
                value={jeAmount}
                onChange={(e) => setJeAmount(e.target.value)}
                placeholder="Balanced Amount (LKR)"
                className="w-full px-3 py-2 rounded-xl bg-[#141F31] border border-white/10 text-xs"
              />
              <button
                type="submit"
                className="w-full py-2.5 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
              >
                Validate & Post Balanced Entry
              </button>
            </form>
          )}
        </div>
      )}

      {tab === "coa" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Hierarchical Chart of Accounts ({accounts.length})</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">GL Code</th>
                <th className="py-2">Account Name</th>
                <th className="py-2">Type</th>
                <th className="py-2">Subtype</th>
                <th className="py-2 text-right">Period Debits</th>
                <th className="py-2 text-right">Period Credits</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.code} className="border-b border-white/5">
                  <td className="py-2 font-mono text-[#648BFF]">{a.code}</td>
                  <td className="py-2 font-medium">{a.name}</td>
                  <td className="py-2">{a.account_type}</td>
                  <td className="py-2 text-[#94A3B8]">{a.account_subtype}</td>
                  <td className="py-2 text-right">{formatCurrency(a.period_debit)}</td>
                  <td className="py-2 text-right">{formatCurrency(a.period_credit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "expenses" && (
        <div className="glass-table-container rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-bold">Corporate Expense Register ({expenses.length})</h2>
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Expense #</th>
                <th className="py-2">Category</th>
                <th className="py-2">Vendor / Payee</th>
                <th className="py-2">Date</th>
                <th className="py-2 text-right">Amount (LKR)</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((ex) => (
                <tr key={ex.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#648BFF]">{ex.expense_number}</td>
                  <td className="py-2.5 font-medium">{ex.category}</td>
                  <td className="py-2.5">{ex.vendor_name}</td>
                  <td className="py-2.5">{formatDate(ex.expense_date)}</td>
                  <td className="py-2.5 text-right font-bold text-[#F4B740]">
                    {formatCurrency(ex.total_amount)}
                  </td>
                  <td className="py-2.5">{ex.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 7. PROJECTS, KANBAN BOARD & WORKFLOW APPROVAL CENTER
// ============================================================================
export const ProjectsAndWorkflowsView: React.FC<{
  mode?: "projects" | "tasks" | "approvals";
}> = ({ mode = "projects" }) => {
  const { user, hasPermission } = useAuth();
  const [projects, setProjects] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [pRes, tRes, aRes] = await Promise.all([
        apiRequest("/projects"),
        apiRequest("/tasks"),
        apiRequest("/workflows/approvals"),
      ]);
      setProjects(pRes.items || []);
      setTasks(tRes.items || []);
      setApprovals(aRes.items || []);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    loadData();
  }, [user?.organization_id]);

  const handleMoveTask = async (taskId: string, nextStatus: string) => {
    await apiRequest(`/tasks/${taskId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    });
    loadData();
  };

  const handleWorkflowAction = async (appId: string, action: "APPROVE" | "REJECT") => {
    setErr(null);
    setMsg(null);
    try {
      const res = await apiRequest(`/workflows/approvals/${appId}/act`, {
        method: "POST",
        body: JSON.stringify({
          action,
          comments: action === "REJECT" ? "Rejected during audit review" : "Approved via Workflow Engine",
        }),
      });
      setMsg(`Document ${res.document_number} workflow updated to ${res.status} (Step ${res.current_step_order}).`);
      loadData();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  if (mode === "approvals") {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[#648BFF]" />
            Reusable Multi-Tier Workflow & Approval Center
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Transactions &le; LKR 50,000: 1-Step Dept Manager • Transactions &gt; LKR 50,000: 2-Step Dept + Finance Manager • Self-Approval Blocked
          </p>
        </div>
        {msg && <div className="p-3 rounded-xl bg-[#20C997]/15 text-xs text-[#20C997]">{msg}</div>}
        {err && <div className="p-3 rounded-xl bg-[#F06464]/15 text-xs text-[#F06464]">{err}</div>}

        <div className="glass-table-container rounded-2xl p-5">
          <table className="w-full text-xs tabular-nums">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Document</th>
                <th className="py-2">Type</th>
                <th className="py-2">Requested By</th>
                <th className="py-2 text-right">Amount (LKR)</th>
                <th className="py-2">Step Progress</th>
                <th className="py-2">Status</th>
                <th className="py-2 text-right">Decision</th>
              </tr>
            </thead>
            <tbody>
              {approvals.map((a) => (
                <tr key={a.id} className="border-b border-white/5">
                  <td className="py-2.5 font-mono text-[#648BFF]">{a.document_number}</td>
                  <td className="py-2.5">{a.document_type}</td>
                  <td className="py-2.5">{a.requested_by_name}</td>
                  <td className="py-2.5 text-right font-bold">{formatCurrency(a.amount)}</td>
                  <td className="py-2.5">
                    Step {a.current_step_order} of {a.total_steps_required}
                  </td>
                  <td className="py-2.5">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] ${
                        a.status === "APPROVED"
                          ? "bg-[#20C997]/20 text-[#20C997]"
                          : a.status === "REJECTED"
                          ? "bg-[#F06464]/20 text-[#F06464]"
                          : "bg-[#F4B740]/20 text-[#F4B740]"
                      }`}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td className="py-2.5 text-right space-x-1.5">
                    {a.status === "PENDING" && hasPermission("approvals.act") && (
                      <>
                        <button
                          onClick={() => handleWorkflowAction(a.id, "APPROVE")}
                          className="px-2.5 py-1 rounded bg-[#20C997]/20 text-[#20C997] text-[11px]"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleWorkflowAction(a.id, "REJECT")}
                          className="px-2.5 py-1 rounded bg-[#F06464]/20 text-[#F06464] text-[11px]"
                        >
                          Reject
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const columns = ["BACKLOG", "TODO", "IN_PROGRESS", "REVIEW", "DONE"];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2">
          <FolderKanban className="w-5 h-5 text-[#648BFF]" />
          Enterprise Projects, Budgets & Interactive Kanban Board
        </h1>
        <p className="text-xs text-[#94A3B8]">
          Click any task stage button on the Kanban cards below to transition task status in real time.
        </p>
      </div>

      {/* Project Portfolio Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {projects.map((p) => (
          <div key={p.id} className="glass-panel rounded-2xl p-4 space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-[#648BFF]">{p.project_code}</span>
              <span className="px-2 py-0.5 rounded bg-[#8B7CFF]/20 text-[#8B7CFF] text-[10px]">
                {p.priority}
              </span>
            </div>
            <h3 className="text-sm font-bold leading-snug">{p.name}</h3>
            <div className="w-full bg-white/10 h-2 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-[#648BFF] to-[#20C997] h-full"
                style={{ width: `${p.progress_percent}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-[#94A3B8] tabular-nums">
              <span>Progress: {p.progress_percent}%</span>
              <span>Budget: {formatCurrency(p.budget, "LKR", true)}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Interactive 5-Column Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {columns.map((col) => {
          const colTasks = tasks.filter((t) => t.status === col);
          return (
            <div key={col} className="glass-panel rounded-2xl p-3.5 space-y-3">
              <div className="flex items-center justify-between text-xs font-bold border-b border-white/10 pb-2">
                <span>{col.replace("_", " ")}</span>
                <span className="px-2 py-0.5 rounded-full bg-white/10 text-[10px]">
                  {colTasks.length}
                </span>
              </div>
              <div className="space-y-2.5">
                {colTasks.map((t) => (
                  <div
                    key={t.id}
                    className="p-3 rounded-xl bg-[#141F31]/90 border border-white/10 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between text-[10px] text-[#94A3B8]">
                      <span className="font-mono text-[#648BFF]">{t.task_code}</span>
                      <span>{t.priority}</span>
                    </div>
                    <div className="font-medium leading-snug">{t.title}</div>
                    <div className="text-[10px] text-[#94A3B8]">Due: {formatDate(t.due_date)}</div>
                    <div className="flex flex-wrap gap-1 pt-1">
                      {columns
                        .filter((c) => c !== col)
                        .map((nextCol) => (
                          <button
                            key={nextCol}
                            onClick={() => handleMoveTask(t.id, nextCol)}
                            className="px-1.5 py-0.5 rounded bg-white/5 hover:bg-[#648BFF]/30 text-[9px] text-[#94A3B8] hover:text-white"
                          >
                            → {nextCol.replace("_", " ")}
                          </button>
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// 8. NEXORA INTELLIGENCE — AI & MACHINE LEARNING ENGINE VIEW
// ============================================================================
export const NexoraIntelligenceView: React.FC<{
  activeFeature?: "insights" | "demand" | "sales" | "anomalies" | "copilot";
}> = ({ activeFeature = "demand" }) => {
  const { user } = useAuth();
  const [tab, setTab] = useState(activeFeature);
  const [insights, setInsights] = useState<any[]>([]);
  const [demandData, setDemandData] = useState<any | null>(null);
  const [salesForecast, setSalesForecast] = useState<any | null>(null);
  const [anomalyData, setAnomalyData] = useState<any | null>(null);
  const [modelChoice, setModelChoice] = useState("XGBOOST");
  const [loadingAI, setLoadingAI] = useState(false);

  // Copilot state
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);

  useEffect(() => {
    setTab(activeFeature);
  }, [activeFeature]);

  const runAllAIModels = async (selectedAlgo: string = modelChoice) => {
    setLoadingAI(true);
    try {
      const [insRes, demRes, salRes, anomRes] = await Promise.all([
        apiRequest("/ai/insights"),
        apiRequest("/ai/forecast/inventory", {
          method: "POST",
          body: JSON.stringify({ model_choice: selectedAlgo }),
        }),
        apiRequest("/ai/forecast/sales", {
          method: "POST",
          body: JSON.stringify({ horizon_months: 6 }),
        }),
        apiRequest("/ai/anomalies/analyze", { method: "POST" }),
      ]);
      setInsights(insRes.items || []);
      setDemandData(demRes);
      setSalesForecast(salRes);
      setAnomalyData(anomRes);
    } catch {
      // Ignore if role lacks specific AI permission
    } finally {
      setLoadingAI(false);
    }
  };

  useEffect(() => {
    runAllAIModels();
  }, [user?.organization_id]);

  const askCopilot = async (promptText: string) => {
    if (!promptText.trim()) return;
    setLoadingAI(true);
    try {
      const res = await apiRequest("/ai/copilot/chat", {
        method: "POST",
        body: JSON.stringify({
          question: promptText,
          conversation_id: conversationId,
        }),
      });
      setConversationId(res.conversation_id);
      setChatHistory((prev) => [...prev, res]);
      setQuestion("");
    } catch (e: any) {
      setChatHistory((prev) => [
        ...prev,
        {
          question: promptText,
          answer: `Error: ${e.message}`,
          source_references: [],
          factual_data: {},
        },
      ]);
    } finally {
      setLoadingAI(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#8B7CFF]" />
            Nexora Intelligence — Machine Learning & Enterprise AI Copilot
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Transparent Evaluation Metrics (MAE, RMSE, WAPE) • 90% Prediction Intervals • Isolation Forest Anomaly Detection • Permission-Scoped Copilot
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: "insights", label: "AI Insights" },
            { id: "demand", label: "Demand Forecasting" },
            { id: "sales", label: "Sales Forecasting" },
            { id: "anomalies", label: "Anomaly Detection" },
            { id: "copilot", label: "AI Copilot" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium ${
                tab === t.id
                  ? "bg-gradient-to-r from-[#648BFF] to-[#8B7CFF] text-white"
                  : "glass-panel text-[#94A3B8]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === "insights" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {insights.map((ins) => (
            <div key={ins.id} className="glass-panel rounded-2xl p-5 space-y-3 border border-[#8B7CFF]/30">
              <div className="flex items-center justify-between text-xs">
                <span className="px-2.5 py-0.5 rounded-full bg-[#8B7CFF]/20 text-[#8B7CFF] font-semibold">
                  {ins.category}
                </span>
                <span className="text-[#20C997] font-mono">
                  Confidence: {(ins.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
              <h3 className="text-base font-bold">{ins.title}</h3>
              <p className="text-xs text-[#94A3B8] leading-relaxed">{ins.summary}</p>
              <div className="pt-2 border-t border-white/10 text-xs text-[#20C997] font-semibold">
                Impact: {ins.impact_estimate}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "demand" && demandData && (
        <div className="space-y-5">
          {/* Model Evaluation Header */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 tabular-nums">
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">Active ML Model</div>
              <select
                value={modelChoice}
                onChange={(e) => {
                  setModelChoice(e.target.value);
                  runAllAIModels(e.target.value);
                }}
                className="mt-1 w-full bg-[#141F31] border border-white/10 rounded-lg px-2 py-1 text-xs font-bold text-[#648BFF]"
              >
                <option value="XGBOOST">XGBoost / Gradient Boosting</option>
                <option value="SEASONAL_NAIVE">Seasonal Naive Baseline</option>
                <option value="MOVING_AVERAGE">Moving Average Baseline</option>
              </select>
            </div>
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">MAE (Mean Abs Error)</div>
              <div className="text-lg font-bold text-[#20C997] mt-1">
                {demandData.evaluation_metrics?.mae}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">RMSE (Root Mean Sq Error)</div>
              <div className="text-lg font-bold text-[#648BFF] mt-1">
                {demandData.evaluation_metrics?.rmse}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">WAPE (%)</div>
              <div className="text-lg font-bold text-[#8B7CFF] mt-1">
                {demandData.evaluation_metrics?.wape_percent}%
              </div>
            </div>
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">Critical / High Stockout Risk</div>
              <div className="text-lg font-bold text-[#F06464] mt-1">
                {demandData.summary?.critical_stockout_risk_count} Critical /{" "}
                {demandData.summary?.high_stockout_risk_count} High
              </div>
            </div>
          </div>

          <div className="glass-table-container rounded-2xl p-5 space-y-3">
            <h2 className="text-sm font-bold">
              Product Demand Forecasts (7-Day, 30-Day & 90-Day Horizons + 90% Prediction Intervals)
            </h2>
            <div className="overflow-x-auto max-h-[480px]">
              <table className="w-full text-xs tabular-nums">
                <thead>
                  <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                    <th className="py-2">SKU</th>
                    <th className="py-2">Product</th>
                    <th className="py-2 text-right">Current Stock</th>
                    <th className="py-2 text-right">7D Demand</th>
                    <th className="py-2 text-right">30D Demand</th>
                    <th className="py-2 text-right">90% Interval (30D)</th>
                    <th className="py-2 text-right">90D Demand</th>
                    <th className="py-2">Stockout Risk</th>
                    <th className="py-2 text-right">Suggested Reorder</th>
                  </tr>
                </thead>
                <tbody>
                  {(demandData.forecasts || []).map((f: any) => (
                    <tr key={f.sku} className="border-b border-white/5">
                      <td className="py-2 font-mono text-[#648BFF]">{f.sku}</td>
                      <td className="py-2 font-medium">{f.product_name}</td>
                      <td className="py-2 text-right font-bold">{f.current_stock}</td>
                      <td className="py-2 text-right">{f.forecast_7d}</td>
                      <td className="py-2 text-right font-semibold text-[#648BFF]">
                        {f.forecast_30d}
                      </td>
                      <td className="py-2 text-right text-[#94A3B8]">
                        [{f.lower_bound_30d} – {f.upper_bound_30d}]
                      </td>
                      <td className="py-2 text-right">{f.forecast_90d}</td>
                      <td className="py-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            f.stockout_risk === "CRITICAL"
                              ? "bg-[#F06464]/20 text-[#F06464]"
                              : f.stockout_risk === "HIGH"
                              ? "bg-[#F4B740]/20 text-[#F4B740]"
                              : "bg-[#20C997]/20 text-[#20C997]"
                          }`}
                        >
                          {f.stockout_risk}
                        </span>
                      </td>
                      <td className="py-2 text-right font-bold text-[#20C997]">
                        +{f.suggested_reorder_qty} {f.uom}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === "sales" && salesForecast && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 tabular-nums">
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">Next Month Predicted Revenue</div>
              <div className="text-lg font-bold text-[#20C997] mt-1">
                {formatCurrency(salesForecast.next_month_predicted_revenue)}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">6-Month Horizon Total</div>
              <div className="text-lg font-bold text-[#648BFF] mt-1">
                {formatCurrency(salesForecast.total_horizon_predicted_revenue)}
              </div>
            </div>
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">Model WAPE (%)</div>
              <div className="text-lg font-bold text-[#8B7CFF] mt-1">
                {salesForecast.evaluation_metrics?.wape_percent}%
              </div>
            </div>
            <div className="glass-panel p-4 rounded-2xl">
              <div className="text-xs text-[#94A3B8]">Prediction Interval</div>
              <div className="text-lg font-bold text-white mt-1">90% Confidence Band</div>
            </div>
          </div>

          <div className="glass-table-container rounded-2xl p-5">
            <h2 className="text-sm font-bold mb-3">
              Actual Historical Revenue vs. Forecasted Monthly Revenue Trajectory
            </h2>
            <table className="w-full text-xs tabular-nums">
              <thead>
                <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                  <th className="py-2">Period</th>
                  <th className="py-2">Segment</th>
                  <th className="py-2 text-right">Actual Revenue</th>
                  <th className="py-2 text-right">Model Prediction</th>
                  <th className="py-2 text-right">90% Lower Bound</th>
                  <th className="py-2 text-right">90% Upper Bound</th>
                </tr>
              </thead>
              <tbody>
                {(salesForecast.timeline || []).map((row: any) => (
                  <tr key={row.period_key} className="border-b border-white/5">
                    <td className="py-2 font-medium">{row.period}</td>
                    <td className="py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          row.type === "ACTUAL"
                            ? "bg-[#648BFF]/20 text-[#648BFF]"
                            : "bg-[#8B7CFF]/20 text-[#8B7CFF]"
                        }`}
                      >
                        {row.type}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      {row.actual_revenue !== null ? formatCurrency(row.actual_revenue) : "—"}
                    </td>
                    <td className="py-2 text-right font-bold text-[#20C997]">
                      {formatCurrency(row.predicted_revenue)}
                    </td>
                    <td className="py-2 text-right text-[#94A3B8]">
                      {formatCurrency(row.lower_bound)}
                    </td>
                    <td className="py-2 text-right text-[#94A3B8]">
                      {formatCurrency(row.upper_bound)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "anomalies" && anomalyData && (
        <div className="space-y-4">
          <div className="p-4 rounded-2xl glass-panel border border-[#F4B740]/40 text-xs text-[#F4B740]">
            <strong>Human-in-the-Loop Audit Policy:</strong> {anomalyData.disclaimer}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(anomalyData.events || []).map((ev: any) => (
              <div
                key={ev.id}
                className="glass-panel rounded-2xl p-5 space-y-3 border border-[#F06464]/30"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-bold text-[#F06464]">
                    {ev.domain} • {ev.reference_number}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#F06464]/20 text-[#F06464] font-mono">
                    Score: {ev.anomaly_score} ({ev.severity})
                  </span>
                </div>
                <h3 className="text-sm font-bold">{ev.title}</h3>
                <p className="text-xs text-[#94A3B8] leading-relaxed">{ev.reason}</p>
                <div className="p-2.5 rounded-xl bg-white/5 text-xs text-[#20C997]">
                  <strong>Recommended Review:</strong> {ev.recommended_action}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "copilot" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 glass-panel rounded-2xl p-5 flex flex-col h-[560px]">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-[#8B7CFF]" />
                <span className="text-sm font-bold">Nexora Conversational AI Business Copilot</span>
              </div>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#20C997]/20 text-[#20C997]">
                Read-Only • Tenant & RBAC Scoped
              </span>
            </div>

            <div className="flex-1 overflow-y-auto py-4 space-y-4">
              {chatHistory.length === 0 && (
                <div className="text-center py-12 space-y-2 text-xs text-[#94A3B8]">
                  <Sparkles className="w-8 h-8 text-[#8B7CFF] mx-auto mb-2" />
                  <p className="text-sm font-semibold text-white">
                    Ask Nexora AI Copilot about live financial, inventory, supplier, or project performance.
                  </p>
                  <p>Select any suggested question on the right or type your own below.</p>
                </div>
              )}

              {chatHistory.map((item, idx) => (
                <div key={idx} className="space-y-3">
                  <div className="flex justify-end">
                    <div className="px-4 py-2.5 rounded-2xl bg-[#648BFF] text-white text-xs max-w-lg">
                      {item.question}
                    </div>
                  </div>
                  <div className="p-4 rounded-2xl bg-[#141F31] border border-white/10 text-xs space-y-3">
                    <div className="whitespace-pre-line leading-relaxed">{item.answer}</div>
                    {item.source_references?.length > 0 && (
                      <div className="pt-2 border-t border-white/10 flex flex-wrap gap-1.5">
                        {item.source_references.map((s: string, si: number) => (
                          <span
                            key={si}
                            className="px-2 py-0.5 rounded bg-white/10 text-[10px] font-mono text-[#648BFF]"
                          >
                            Source: {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                askCopilot(question);
              }}
              className="pt-3 border-t border-white/10 flex gap-2"
            >
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask e.g. 'What were our total expenses this month?' or 'Which products need replenishment?'"
                className="flex-1 px-4 py-2.5 rounded-xl bg-[#141F31] border border-white/10 text-xs focus:outline-none focus:border-[#648BFF]"
              />
              <button
                type="submit"
                disabled={loadingAI}
                className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#648BFF] to-[#8B7CFF] text-white text-xs font-semibold flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" /> Ask Copilot
              </button>
            </form>
          </div>

          <div className="lg:col-span-4 glass-panel rounded-2xl p-5 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#8B7CFF]">
              Suggested Analytical Prompts
            </h3>
            {[
              "What were our total expenses this month?",
              "Which products need replenishment?",
              "Show our highest-value suppliers.",
              "Compare revenue and profitability across periods.",
              "Which projects are behind schedule?",
              "Approve purchase order PO-2026-305 automatically",
            ].map((q) => (
              <button
                key={q}
                onClick={() => askCopilot(q)}
                className="w-full p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-left text-xs transition"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 9. SYSTEM, REPORTS, AUDIT LOGS, USERS & SETTINGS MODULE
// ============================================================================
export const SystemAdminView: React.FC<{
  section: "reports" | "notifications" | "audit-logs" | "users-permissions" | "settings";
}> = ({ section }) => {
  const { user, toggleTheme, theme } = useAuth();
  const [reportType, setReportType] = useState("trial-balance");
  const [reportData, setReportData] = useState<any | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [mfaSetupData, setMfaSetupData] = useState<any | null>(null);

  useEffect(() => {
    if (section === "reports") {
      apiRequest(`/analytics/reports/${reportType}`).then(setReportData).catch(() => {});
    } else if (section === "audit-logs") {
      apiRequest("/audit-logs").then((r) => setAuditLogs(r.items || [])).catch(() => {});
    } else if (section === "users-permissions") {
      Promise.all([apiRequest("/users"), apiRequest("/roles")])
        .then(([uRes, rRes]) => {
          setUsers(uRes.items || []);
          setRoles(rRes.items || []);
        })
        .catch(() => {});
    } else if (section === "notifications") {
      apiRequest("/notifications").then((r) => setNotifications(r.items || [])).catch(() => {});
    }
  }, [section, reportType, user?.organization_id]);

  if (section === "reports") {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-[#648BFF]" />
              Enterprise Business Intelligence Reports
            </h1>
            <p className="text-xs text-[#94A3B8]">
              Live database reporting with instant CSV & Printable PDF Export
            </p>
          </div>
          <div className="flex items-center gap-2">
            {[
              { id: "trial-balance", label: "Trial Balance" },
              { id: "invoice-aging", label: "Invoice Aging" },
              { id: "supplier-performance", label: "Supplier Performance" },
              { id: "stock-valuation", label: "Stock Valuation" },
            ].map((rt) => (
              <button
                key={rt.id}
                onClick={() => setReportType(rt.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium ${
                  reportType === rt.id ? "bg-[#648BFF] text-white" : "glass-panel text-[#94A3B8]"
                }`}
              >
                {rt.label}
              </button>
            ))}
            {reportData?.rows && (
              <button
                onClick={() => exportRowsToCSV(`nexora_${reportType}.csv`, reportData.rows)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#20C997] text-[#080D18] text-xs font-bold"
              >
                <Download className="w-3.5 h-3.5" /> Export CSV
              </button>
            )}
          </div>
        </div>

        {reportData && (
          <div className="glass-table-container rounded-2xl p-5 overflow-x-auto">
            <h2 className="text-sm font-bold mb-3">{reportData.report_type}</h2>
            <table className="w-full text-xs tabular-nums">
              <thead>
                <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                  {(reportData.columns || []).map((c: string) => (
                    <th key={c} className="py-2 uppercase">
                      {c.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(reportData.rows || []).map((r: any, idx: number) => (
                  <tr key={idx} className="border-b border-white/5">
                    {(reportData.columns || []).map((c: string) => (
                      <td key={c} className="py-2">
                        {String(r[c] ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  if (section === "audit-logs") {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold">Immutable Security & Operational Audit Trail</h1>
        <div className="glass-table-container rounded-2xl p-5">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                <th className="py-2">Timestamp</th>
                <th className="py-2">Actor</th>
                <th className="py-2">Action</th>
                <th className="py-2">Entity</th>
                <th className="py-2">Correlation ID</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((l) => (
                <tr key={l.id} className="border-b border-white/5">
                  <td className="py-2 font-mono text-[11px]">{formatDate(l.created_at)}</td>
                  <td className="py-2 text-[#648BFF]">{l.actor_email}</td>
                  <td className="py-2 font-semibold">{l.action}</td>
                  <td className="py-2">{l.entity_type}</td>
                  <td className="py-2 font-mono text-[#94A3B8]">{l.correlation_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (section === "users-permissions") {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold">Enterprise Users & 12-Role RBAC Matrix</h1>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-table-container rounded-2xl p-5 space-y-3">
            <h2 className="text-sm font-bold">Tenant Users ({users.length})</h2>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[#94A3B8] border-b border-white/10 text-left">
                  <th className="py-2">Name</th>
                  <th className="py-2">Email</th>
                  <th className="py-2">Assigned Roles</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-white/5">
                    <td className="py-2 font-medium">{u.full_name}</td>
                    <td className="py-2 font-mono text-[#648BFF]">{u.email}</td>
                    <td className="py-2">{u.roles.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="glass-table-container rounded-2xl p-5 space-y-3">
            <h2 className="text-sm font-bold">Configured RBAC Roles ({roles.length})</h2>
            <div className="space-y-2.5 max-h-[460px] overflow-y-auto">
              {roles.map((r) => (
                <div key={r.id} className="p-3 rounded-xl bg-white/5 border border-white/10 text-xs">
                  <div className="flex justify-between font-bold">
                    <span className="text-[#648BFF]">{r.name} ({r.code})</span>
                    <span>{r.permissions.length} Permissions</span>
                  </div>
                  <p className="text-[11px] text-[#94A3B8] mt-1">{r.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (section === "notifications") {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold">Enterprise Notification Center</h1>
        <div className="space-y-2.5">
          {notifications.map((n) => (
            <div key={n.id} className="glass-panel rounded-2xl p-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-bold">{n.title}</div>
                <div className="text-xs text-[#94A3B8] mt-0.5">{n.message}</div>
              </div>
              <span className="text-xs font-mono text-[#648BFF]">{n.category}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-xl font-bold">System, Security & Appearance Settings</h1>
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-bold">Interface Theme Mode</div>
            <div className="text-xs text-[#94A3B8]">
              Persist Dark or Light Glassmorphism theme across sessions
            </div>
          </div>
          <button
            onClick={toggleTheme}
            className="px-4 py-2 rounded-xl bg-[#648BFF] text-white text-xs font-semibold"
          >
            Current: {theme.toUpperCase()} (Click to Toggle)
          </button>
        </div>

        <div className="pt-4 border-t border-white/10 flex items-center justify-between">
          <div>
            <div className="text-sm font-bold">TOTP Multi-Factor Authentication (RFC 6238)</div>
            <div className="text-xs text-[#94A3B8]">
              Generate a cryptographic Base32 secret for Authenticator apps
            </div>
          </div>
          <button
            onClick={async () => {
              const res = await apiRequest("/auth/mfa/setup", { method: "POST" });
              setMfaSetupData(res);
            }}
            className="px-4 py-2 rounded-xl bg-[#8B7CFF] text-white text-xs font-semibold"
          >
            Provision TOTP Secret
          </button>
        </div>

        {mfaSetupData && (
          <div className="p-4 rounded-xl bg-[#141F31] border border-[#8B7CFF]/40 text-xs space-y-1.5 font-mono">
            <div>Secret: {mfaSetupData.secret}</div>
            <div>Current 6-Digit Code: {mfaSetupData.current_demo_code}</div>
          </div>
        )}
      </div>
    </div>
  );
};
