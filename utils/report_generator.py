import pandas as pd
from fpdf import FPDF
import datetime

class DataQualityReport(FPDF):
    def header(self):
        # Header title
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'DataTrust AI: Intelligent Automated Data Quality Management System', 0, 1, 'C')
        self.ln(10)
        
    def footer(self):
        # Footer page number
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def generate_report(df, filename, metrics, quality_score, errors):
    """
    Generates a PDF data quality report.
    """
    pdf = DataQualityReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # 1. Title and basic info
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Data Quality Analysis Report', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'L')
    pdf.cell(0, 10, f'Dataset Name: {filename}', 0, 1, 'L')
    pdf.ln(5)
    
    # 2. Overall Quality Score
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Overall Quality Score', 0, 1, 'L')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Score: {quality_score}%', 0, 1, 'L')
    pdf.ln(5)
    
    # 3. Data Summary
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Data Summary', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f'Total Rows: {len(df)}', 0, 1, 'L')
    pdf.cell(0, 10, f'Total Columns: {len(df.columns)}', 0, 1, 'L')
    pdf.cell(0, 10, f'Duplicate Rows: {df.duplicated().sum()}', 0, 1, 'L')
    pdf.ln(5)
    
    # 4. Column-wise metrics
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Column-wise Quality Metrics', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    
    # Add table header
    pdf.cell(60, 10, 'Column Name', 1)
    pdf.cell(40, 10, 'Data Type', 1)
    pdf.cell(40, 10, 'Missing Count', 1)
    pdf.cell(40, 10, 'Missing (%)', 1)
    pdf.ln()
    
    for column, m in metrics.items():
        pdf.cell(60, 10, column, 1)
        pdf.cell(40, 10, m['data_type'], 1)
        pdf.cell(40, 10, str(m['missing_count']), 1)
        pdf.cell(40, 10, f"{m['missing_percentage']}%", 1)
        pdf.ln()
    pdf.ln(5)
    
    # 5. Potential Errors
    if errors:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Potential Data Errors', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        for error in errors:
            pdf.multi_cell(0, 10, f"- {error}")
            pdf.ln(2)
            
    # Save PDF
    output_path = f"outputs/report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(output_path)
    return output_path
