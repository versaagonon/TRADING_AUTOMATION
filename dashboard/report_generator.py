from fpdf import FPDF
import datetime
import pandas as pd

class TradingReport(FPDF):
    def header(self):
        # Header Dark 411 Style
        self.set_fill_color(2, 6, 23)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, '411 BOT AI | PERFORMANCE AUDIT', ln=True, align='C')
        self.set_font('helvetica', '', 10)
        self.cell(0, 5, f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} | Proprietary Audit - Master Versaa 411', align='C')

def generate_pdf(filename, initial_balance, final_balance, trades, strategy_name="Unknown", coin="BTC/USDT"):
    pdf = TradingReport()
    pdf.add_page()
    
    # CALCULATE STATISTICS
    total_profit = final_balance - initial_balance
    roi = (total_profit / initial_balance) * 100 if initial_balance > 0 else 0
    
    duration_str = "-"
    daily_avg = 0
    monthly_avg = 0
    yearly_avg = 0
    
    if trades:
        try:
            df_trades = pd.DataFrame(trades)
            df_trades['date'] = pd.to_datetime(df_trades['date'])
            start_date = df_trades['date'].min()
            end_date = df_trades['date'].max()
            duration = end_date - start_date
            duration_days = max(duration.days, 1)
            duration_months = max(duration_days / 30.44, 1)
            duration_years = max(duration_days / 365.25, 1)
            
            duration_str = f"{duration_days} Days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
            daily_avg = total_profit / duration_days
            monthly_avg = total_profit / duration_months
            yearly_avg = total_profit / duration_years
        except Exception as e:
            print(f"Stat Error: {e}")

    # Section 1: Core Performance
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(2, 6, 23)
    pdf.cell(0, 10, 'I. STRATEGY & ENGINE CONFIGURATION', ln=True)
    pdf.set_font('helvetica', '', 10)
    
    config_data = [
        ['Trading Strategy', strategy_name.upper()],
        ['Asset Pair', coin],
        ['Simulation Duration', duration_str],
        ['Initial Capital', f'${initial_balance:,.2f}']
    ]
    
    for row in config_data:
        pdf.cell(60, 8, row[0], border='B')
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(0, 8, row[1], border='B', ln=True)
        pdf.set_font('helvetica', '', 10)

    pdf.ln(5)

    # Section 2: Financial Results
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, 'II. FINANCIAL GROWTH ANALYSIS', ln=True)
    
    # Financial Table
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 10, 'Metric Description', border=1, fill=True)
    pdf.cell(95, 10, 'Value Output', border=1, fill=True, ln=True)
    
    pdf.set_font('helvetica', '', 10)
    fin_data = [
        ['Applied Strategy', strategy_name.upper()],
        ['Final Equity', f'${final_balance:,.2f}'],
        ['Total Net Profit', f'${total_profit:,.2f}'],
        ['Total ROI', f'{roi:.2f}%'],
        ['Avg. Daily Profit', f'${daily_avg:,.2f}/day'],
        ['Avg. Monthly Profit', f'${monthly_avg:,.2f}/month'],
        ['Avg. Yearly Profit (Est.)', f'${yearly_avg:,.2f}/year']
    ]
    
    for row in fin_data:
        pdf.cell(95, 10, row[0], border=1)
        pdf.set_font('helvetica', 'B', 10)
        if 'Profit' in row[0] and total_profit < 0: pdf.set_text_color(180, 0, 0)
        elif 'Profit' in row[0] and total_profit > 0: pdf.set_text_color(0, 120, 0)
        pdf.cell(95, 10, row[1], border=1, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('helvetica', '', 10)

    pdf.ln(10)

    # Section 3: Trade History (Samples)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, 'III. OPERATIONAL LOGS (RECENT TRADES)', ln=True)
    
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_fill_color(2, 6, 23)
    pdf.set_text_color(255, 255, 255)
    
    headers = ['Date', 'Type', 'Entry/Exit Price', 'Final Balance', 'Status']
    col_widths = [45, 30, 40, 45, 30]
    
    for i in range(len(headers)):
        pdf.cell(col_widths[i], 8, headers[i], border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font('helvetica', '', 8)
    
    # Show last 25 trades for clarity
    display_trades = trades[-25:] if len(trades) > 0 else []
    for t in display_trades:
        pdf.cell(col_widths[0], 7, str(t['date']), border=1)
        pdf.cell(col_widths[1], 7, str(t['type']), border=1, align='C')
        pdf.cell(col_widths[2], 7, f"${t['price']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[3], 7, f"${t['balance']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[4], 7, str(t['result']), border=1, align='C', ln=True)

    if len(trades) > 25:
        pdf.ln(2)
        pdf.set_font('helvetica', 'I', 8)
        pdf.cell(0, 10, f'* Showing recent 25 trades out of {len(trades)} total operations.', align='R')

    pdf.ln(10)

    # Section 4: Executive Performance Summary (Requested by Master Versaa)
    pdf.set_fill_color(2, 6, 23)
    pdf.rect(10, pdf.get_y(), 190, 25, 'F')
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 5, 'IV. EXECUTIVE PERFORMANCE SUMMARY', ln=True, align='C')
    pdf.ln(2)
    
    # STRATEGY | MODAL | PROFIT % | TIMESTAMP | MATA UANG
    summary_text = f"{strategy_name.upper()} | ${initial_balance:,.2f} | {roi:+.2f}% | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | {coin}"
    pdf.set_font('courier', 'B', 10)
    pdf.cell(0, 8, summary_text, ln=True, align='C')
    
    pdf.output(filename)
    return filename

def generate_csv_summary(filename, initial_balance, final_balance, trades, strategy_name="Unknown", coin="BTC/USDT"):
    import csv
    
    total_profit = final_balance - initial_balance
    roi = (total_profit / initial_balance) * 100 if initial_balance > 0 else 0
    
    duration_str = "-"
    daily_avg_pct = 0
    monthly_avg_pct = 0
    yearly_avg_pct = 0
    max_drawdown_pct = 0
    lose_rate_pct = 0
    
    if trades:
        try:
            df_trades = pd.DataFrame(trades)
            
            # Max Drawdown Calculation
            if not df_trades.empty:
                # Kita hitung dari balance history
                running_max = df_trades['balance'].cummax()
                drawdown = (running_max - df_trades['balance']) / running_max
                max_drawdown_pct = drawdown.max() * 100
                
                # Lose Rate Calculation (Exclude ENTRIES)
                actual_trades = df_trades[df_trades['result'] != 'ENTRY']
                if len(actual_trades) > 0:
                    losses = len(actual_trades[actual_trades['result'] == 'LOSS'])
                    lose_rate_pct = (losses / len(actual_trades)) * 100

            # Time Stats
            df_trades['date'] = pd.to_datetime(df_trades['date'])
            start_date = df_trades['date'].min()
            end_date = df_trades['date'].max()
            duration_days = max((end_date - start_date).days, 1)
            duration_months = max(duration_days / 30.44, 1)
            duration_years = max(duration_days / 365.25, 1)
            
            duration_str = f"{duration_days} Days"
            daily_avg_pct = roi / duration_days
            monthly_avg_pct = roi / duration_months
            yearly_avg_pct = roi / duration_years
        except Exception as e:
            print(f"CSV Stat Error: {e}")

    import os
    file_exists = os.path.isfile(filename) and os.path.getsize(filename) > 0

    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Tulis Header hanya jika file baru
        if not file_exists:
            writer.writerow([
                "strategy", "modal", "avg profit day %", "avg profit month %", 
                "avg profit years %", "Total ROI", "Total Net Profit", 
                "max drawdown %", "lose rate %",
                "Asset Pair", "Simulation Duration", "timestamp"
            ])
        
        # Tambahkan Row Data baru ke urutan terbawah
        writer.writerow([
            strategy_name.upper(),
            f"${initial_balance:.2f}",
            f"{daily_avg_pct:.4f}%",
            f"{monthly_avg_pct:.4f}%",
            f"{yearly_avg_pct:.4f}%",
            f"{roi:.4f}%",
            f"${total_profit:.2f}",
            f"{max_drawdown_pct:.2f}%",
            f"{lose_rate_pct:.2f}%",
            coin,
            duration_str,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        
    return filename
