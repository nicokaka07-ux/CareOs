from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone
from billing.models import Receipt


class Command(BaseCommand):
    help = 'Generate PDF files for Receipt records that have no PDF stored.'

    def handle(self, *args, **options):
        # Prefer WeasyPrint for HTML->PDF; fall back to ReportLab if unavailable.
        HTML = None
        try:
            from weasyprint import HTML as _HTML
            HTML = _HTML
        except Exception:
            HTML = None

        qs = Receipt.objects.filter(pdf_file='') | Receipt.objects.filter(pdf_file__isnull=True)
        count = 0
        for receipt in qs.order_by('generated_at'):
            try:
                html = receipt.content_html
                if not html:
                    line_items = []
                    # try to render invoice print as fallback
                    html = render_to_string('billing/invoice_print.html', {
                        'invoice': receipt.invoice,
                        'payments': getattr(receipt.invoice, 'payments').all(),
                        'line_items': line_items,
                    })

                pdf = None
                if HTML is not None:
                    pdf = HTML(string=html, base_url='/').write_pdf()
                else:
                    # Fallback: produce a very simple PDF with ReportLab
                    try:
                        from reportlab.lib.pagesizes import A4
                        from reportlab.pdfgen import canvas
                        import io

                        buffer = io.BytesIO()
                        c = canvas.Canvas(buffer, pagesize=A4)
                        text = c.beginText(40, 800)
                        lines = []
                        lines.append(f"Receipt: {receipt.receipt_number}")
                        lines.append(f"Invoice: {receipt.invoice.invoice_number}")
                        lines.append("")
                        # Simple invoice lines
                        lines.append(f"Patient: {receipt.invoice.patient.get_full_name()}")
                        lines.append(f"Generated: {receipt.generated_at}")
                        lines.append("")
                        # If content_html is simple, strip tags roughly
                        import re
                        stripped = re.sub('<[^<]+?>', '', html)
                        for part in stripped.splitlines():
                            if part.strip():
                                lines.append(part.strip())

                        for ln in lines:
                            text.textLine(ln)
                        c.drawText(text)
                        c.showPage()
                        c.save()
                        buffer.seek(0)
                        pdf = buffer.read()
                    except Exception as e:
                        self.stderr.write(f'ReportLab fallback failed: {e}')
                        continue

                from django.core.files.base import ContentFile
                filename = f"{receipt.receipt_number}.pdf"
                receipt.pdf_file.save(filename, ContentFile(pdf))
                receipt.save(update_fields=['pdf_file'])
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Generated PDF for {receipt.receipt_number}'))
            except Exception as e:
                self.stderr.write(f'Failed to generate PDF for receipt {receipt.pk}: {e}')

        self.stdout.write(self.style.SUCCESS(f'Done. {count} PDFs generated.'))
