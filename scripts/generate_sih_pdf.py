import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#7a6c62"))
        
        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "CIRIS: Proactive Financial Cybercrime Interception Engine | SIH Master Defense Dossier")
            self.setStrokeColor(colors.HexColor("#d8d0c8"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
            
        # Running Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, page_text)
        self.drawString(54, 36, "SMART INDIA HACKATHON &bull; OFFICIAL JURY EVALUATION & VIVA DEFENSE GUIDE")
        self.setStrokeColor(colors.HexColor("#d8d0c8"))
        self.setLineWidth(0.5)
        self.line(54, 48, letter[0] - 54, 48)
        self.restoreState()

def build_pdf(filename="CIRIS_SIH_Judge_Pitch_Deck.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=50,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # Palette
    PRIMARY = colors.HexColor("#964407")      # Terracotta / Warm Ochre
    PRIMARY_DARK = colors.HexColor("#5c2902") # Deep Bronze
    SECONDARY = colors.HexColor("#974544")    # Crimson Wine
    ACCENT = colors.HexColor("#15BE74")       # Emerald Mint
    DARK = colors.HexColor("#1d1c18")         # Obsidian Body Text
    MUTED = colors.HexColor("#554339")        # Muted Warm Grey
    SURFACE_ALT = colors.HexColor("#f8f4ee")  # Warm Container
    BORDER = colors.HexColor("#d8d0c8")       # Crisp Border
    Q_BG = colors.HexColor("#fdf2ea")         # Question Highlight Box
    
    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY_DARK,
        spaceAfter=3
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=MUTED,
        spaceAfter=10
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=PRIMARY_DARK,
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=PRIMARY,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=DARK,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'BulletPoint',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=DARK,
        leftIndent=10,
        firstLineIndent=-6,
        spaceAfter=2.5
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=PRIMARY_DARK
    )

    q_title_style = ParagraphStyle(
        'QTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12.5,
        textColor=SECONDARY
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=DARK
    )
    
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=PRIMARY_DARK
    )

    story = []
    
    # ---------------------------------------------------------
    # HEADER BANNER
    # ---------------------------------------------------------
    header_table_data = [
        [
            Paragraph("<b>SMART INDIA HACKATHON (SIH) &bull; OFFICIAL EVALUATION &amp; DEFENSE DOSSIER</b>", ParagraphStyle('Badge', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=PRIMARY)),
            Paragraph("<b>STATUS: PRODUCTION VERIFIED (72/72 TESTS PASSING)</b>", ParagraphStyle('BadgeR', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=ACCENT, alignment=2))
        ]
    ]
    header_table = Table(header_table_data, colWidths=[3.7*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=2, spaceAfter=6))
    
    story.append(Paragraph("CIRIS: Cyber Incident Real-time Interception System", title_style))
    story.append(Paragraph("<b>Autonomous Multi-Hop Mule Graph Traversal, Spatial BallTree Indexing &amp; Physical Cash-Out Localization</b>", subtitle_style))
    
    # Executive Summary Card
    exec_card = [
        [
            Paragraph(
                "<b>Executive Summary for SIH Judges:</b> In financial cyber fraud, 80% of victim losses are physically extracted via ATM cash withdrawals within <b>1 to 4 hours</b>, while traditional police response takes <b>24 to 48 hours</b>. <b>CIRIS completely flips the paradigm from post-mortem investigation to real-time physical &amp; digital interception</b>. Using point-in-time graph traversal, 200-kNN geospatial BallTrees, and LightGBM Learning-to-Rank, CIRIS pinpoints the exact ATM terminal where the mule is heading and computes the arrival time window with 4.95h MAE, dispatching encrypted tactical alerts to beat police in sub-50ms.",
                callout_style
            )
        ]
    ]
    t_exec = Table(exec_card, colWidths=[7.2*inch])
    t_exec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), SURFACE_ALT),
        ('BOX', (0,0), (-1,-1), 1, BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_exec)
    story.append(Spacer(1, 6))

    # ---------------------------------------------------------
    # TOPIC 1: THE CORE PROBLEM STATEMENT (WHAT SIH & INDIA NEED)
    # ---------------------------------------------------------
    story.append(Paragraph("Topic 1: Core Problem Statement &amp; The Ground Reality", h1_style))
    story.append(Paragraph("India loses thousands of crores annually to financial cyber fraud (UPI scams, digital arrest, investment APKs, card cloning). The national crisis stems from four systemic operational bottlenecks:", body_style))
    
    story.append(Paragraph("&bull; <b>1. The Critical 4-Hour Cash-Out Asymmetry:</b> Fraudulent money moves through 3–5 layers of digital mule accounts in under 15 minutes. Within 1 to 4 hours, a ground mule physically withdraws the cash at an ATM. Once cash is extracted, money recovery drops to near zero.", bullet_style))
    story.append(Paragraph("&bull; <b>2. The 48-Hour Law Enforcement Delay:</b> After a victim reports to 1930/NCRP, manual FIR registration, Section 91 CrPC notice generation, and bank compliance take 24–48 hours—arriving long after the ATM transaction is complete.", bullet_style))
    story.append(Paragraph("&bull; <b>3. Sub-₹50,000 Micro-Splintering Evasion:</b> Scammers deliberately split large sums (e.g., ₹10 Lakhs) into 25 micro-transactions under ₹50,000 across multiple banks to bypass standard automated Anti-Money Laundering (AML) flags.", bullet_style))
    story.append(Paragraph("&bull; <b>4. Interstate Jurisdictional Blind Spots:</b> A victim scammed in Mumbai transfers to a mule account in Kolkata, while the cash withdrawal occurs at an ATM in Hyderabad. Police at the victim's location have zero visibility over the physical cash-out corridor.", bullet_style))

    story.append(Spacer(1, 4))

    # ---------------------------------------------------------
    # TOPIC 2: TECHNICAL APPROACH & END-TO-END PIPELINE
    # ---------------------------------------------------------
    story.append(Paragraph("Topic 2: Technical Approach &amp; Pipeline Architecture", h1_style))
    story.append(Paragraph("CIRIS executes an autonomous 5-stage intelligence pipeline responding in <b>under 50 milliseconds</b>:", body_style))

    pipe_data = [
        [
            Paragraph("<b>Stage</b>", table_header),
            Paragraph("<b>Core Algorithm &amp; Tech</b>", table_header),
            Paragraph("<b>Detailed Operational Mechanism</b>", table_header),
            Paragraph("<b>Performance Benchmark</b>", table_header)
        ],
        [
            Paragraph("<b>1. Ingestion</b>", table_cell_bold),
            Paragraph("FastAPI, Pydantic v2, SQLite WAL", table_cell),
            Paragraph("Streams NCRP/1930 complaint payload. <b>Locks strict point-in-time boundary (t &le; T_0)</b> to mathematically guarantee zero future lookahead leakage.", table_cell),
            Paragraph("1.2 ms Latency", table_cell)
        ],
        [
            Paragraph("<b>2. Mule Graph</b>", table_cell_bold),
            Paragraph("NetworkX Directed Graph, Fuzzy Match", table_cell),
            Paragraph("Traverses multi-hop transaction rails up to 4 hops. Detects sub-₹50K fan-out splintering and clusters device IDs, IMEI, cards, and phone footprints.", table_cell),
            Paragraph("4 Hops in 4.8 ms", table_cell)
        ],
        [
            Paragraph("<b>3. Spatial GIS</b>", table_cell_bold),
            Paragraph("Scikit-Learn BallTree, R-Tree GIS", table_cell),
            Paragraph("Queries 7,000+ national ATM directory within 250km radius. Intersects candidate pool with <b>Top-1500 historical cashout hotspot clusters</b>.", table_cell),
            Paragraph("200-kNN in 2.7 ms (86% Recall)", table_cell)
        ],
        [
            Paragraph("<b>4. ML Ranking</b>", table_cell_bold),
            Paragraph("LightGBM LambdaMART + Platt Calibration", table_cell),
            Paragraph("Evaluates 43 temporal/spatial features (velocity, proximity, decay rate). Locks Rank #1 Target ATM with <b>Platt-calibrated 95% probability and 4.95h MAE time regressor</b>.", table_cell),
            Paragraph("NDCG@10 = 0.86 (P95 4.5ms)", table_cell)
        ],
        [
            Paragraph("<b>5. Dispatch</b>", table_cell_bold),
            Paragraph("ECDSA, SHA-256 Ledger, WebSockets", table_cell),
            Paragraph("Broadcasts encrypted tactical coordinates to Beat Patrol units &amp; Bank NOCs. Logs tamper-evident cryptographic event ID in SQLite audit trail.", table_cell),
            Paragraph("&lt; 10 ms Broadcast", table_cell)
        ]
    ]

    t_pipe = Table(pipe_data, colWidths=[0.9*inch, 1.7*inch, 3.4*inch, 1.2*inch])
    t_pipe.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, SURFACE_ALT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_pipe)
    story.append(Spacer(1, 6))

    # ---------------------------------------------------------
    # TOPIC 3: FEASIBILITY, PRODUCTION VIABILITY & SCALABILITY
    # ---------------------------------------------------------
    story.append(Paragraph("Topic 3: Feasibility, Production Viability &amp; Scalability", h1_style))
    story.append(Paragraph("&bull; <b>Zero GPU Dependency:</b> The entire pipeline (BallTree spatial search + LightGBM LambdaMART ranker) runs on lightweight standard CPU hardware, requiring zero costly GPU infrastructure.", bullet_style))
    story.append(Paragraph("&bull; <b>Seamless I4C &amp; NPCI Integration:</b> Built entirely on RESTful OpenAPI v3 endpoints compatible with existing National Cybercrime Portal JSON/CSV data streams.", bullet_style))
    story.append(Paragraph("&bull; <b>Rigorously Benchmarked:</b> Seeded and benchmarked on <b>50,000 spatial cases, 7,000 national ATMs, and 150,000 money flow edges</b> with all API latencies below 50ms (P95).", bullet_style))
    story.append(Paragraph("&bull; <b>Human-in-the-Loop Safeguards:</b> Station House Officers (SHOs) and supervisors have instant single-click dispatch, acknowledge, and escalation controls with cryptographic audit logs.", bullet_style))

    # Page Break for Clean Split to Impact & Defense Matrix
    story.append(PageBreak())

    # ---------------------------------------------------------
    # TOPIC 4: REAL-WORLD IMPACT & INNOVATION COMPARISON
    # ---------------------------------------------------------
    story.append(Paragraph("Topic 4: Real-World Field Impact &amp; Comparative Matrix", h1_style))
    story.append(Paragraph("How CIRIS fundamentally transforms law enforcement efficacy compared to the current status quo:", body_style))

    comp_data = [
        [
            Paragraph("<b>Evaluation Dimension</b>", table_header),
            Paragraph("<b>Current Status Quo (NCRP / 1930)</b>", table_header),
            Paragraph("<b>CIRIS Engine (Our Innovation)</b>", table_header)
        ],
        [
            Paragraph("<b>Response Philosophy</b>", table_cell_bold),
            Paragraph("Reactive case registration after cash extraction (24-48 hrs)", table_cell),
            Paragraph("<b>Proactive physical &amp; digital interception in real time (&lt; 3 mins)</b>", table_cell)
        ],
        [
            Paragraph("<b>ATM Localization</b>", table_cell_bold),
            Paragraph("Zero spatial prediction; discovered days later from bank logs", table_cell),
            Paragraph("<b>Pinpointed to specific ATM terminal with 86% NDCG candidate recall</b>", table_cell)
        ],
        [
            Paragraph("<b>Time Window Window</b>", table_cell_bold),
            Paragraph("No timing estimation provided to field units", table_cell),
            Paragraph("<b>Dual-head regressor predicts cashout arrival window (4.95h MAE)</b>", table_cell)
        ],
        [
            Paragraph("<b>Anti-Evasion Detection</b>", table_cell_bold),
            Paragraph("Splits under ₹50,000 evade single-bank AML monitors", table_cell),
            Paragraph("<b>Multi-hop graph engine correlates cross-bank splintering &amp; entity links</b>", table_cell)
        ],
        [
            Paragraph("<b>Field Actionability</b>", table_cell_bold),
            Paragraph("Static text reports and email notices", table_cell),
            Paragraph("<b>Interactive GIS tactical map + live beat patrol dispatch modal</b>", table_cell)
        ],
        [
            Paragraph("<b>Legal Evidence Trail</b>", table_cell_bold),
            Paragraph("Manual case diaries prone to court tampering challenges", table_cell),
            Paragraph("<b>Immutable SHA-256 cryptographic audit ledger (Section 65B compliant)</b>", table_cell)
        ]
    ]

    t_comp = Table(comp_data, colWidths=[1.6*inch, 2.7*inch, 2.9*inch])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_DARK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, SURFACE_ALT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # TOPIC 5: JUDGE CROSS-EXAMINATION DEFENSE GUIDE
    # ---------------------------------------------------------
    story.append(Paragraph("Topic 5: The Tough Questions Judges Will Ask to Tackle Us", h1_style))
    story.append(Paragraph("<b>Be ready with crisp, high-confidence answers when judges try to grill the architecture:</b>", body_style))

    questions = [
        (
            "Q1. 'How do you prove your Machine Learning model didn't cheat using future data?' (Data Leakage Attack)",
            "<b>OUR DEFENSE:</b> 'Sir/Ma'am, we implemented a <b>Strict Point-in-Time Temporal Cutoff ($t \\le T_0$)</b>. During both training and live inference, feature extraction is mathematically bounded at the exact timestamp of complaint ingestion. Transaction edges, account balances, and velocity features created after $T_{\\text{complaint}}$ are strictly masked, ensuring zero future lookahead bias.'"
        ),
        (
            "Q2. 'What if the mule withdraws from a new ATM that never had a scam before?' (Cold-Start Problem)",
            "<b>OUR DEFENSE:</b> 'Our architecture uses a <b>Hybrid Two-Stage Retrieval Engine</b>. Stage 1 uses a 200-kNN BallTree spatial sweep across all 7,000+ national ATMs based on physical distance, transport corridors, and bank networks—not just historical frequency. LambdaMART then evaluates 43 point-in-time features, meaning new or quiet ATMs in the travel radius are accurately scored.'"
        ),
        (
            "Q3. 'Can beat police really reach the ATM in time before the mule leaves?' (Operational Feasibility)",
            "<b>OUR DEFENSE:</b> 'CIRIS predicts the cashout window <b>1 to 4 hours in advance</b> using our Dual-Head Time Regressor (MAE 4.95h), giving beat patrol officers 45 to 90 minutes of lead time. Concurrently, CIRIS triggers an automated digital freeze request to the bank NOC, so even if police are delayed, the account is locked digitally before card insertion.'"
        ),
        (
            "Q4. 'How do you distinguish fraud splintering (< ₹50,000) from innocent family UPI transfers?' (False Positives)",
            "<b>OUR DEFENSE:</b> 'We do not flag transactions based on amount alone. CIRIS computes a <b>Graph Splintering Velocity Metric</b>: fan-out entropy, rapid hop-velocity (< 3 mins between hops), new unverified beneficiary creation, and fuzzy entity clustering (shared device UUIDs / card fingerprints). Genuine family remittances lack this high-velocity multi-layering signature.'"
        ),
        (
            "Q5. 'How does this integrate across different banks without waiting days for NPCI data?' (Interoperability)",
            "<b>OUR DEFENSE:</b> 'CIRIS is designed to sit directly on top of the <b>I4C / 1930 National Cybercrime Reporting Portal pipeline</b>. When a complaint is lodged, transaction reference numbers (RRNs) and bank identifiers are parsed immediately via RESTful OpenAPI endpoints, triggering automated API ledger traversal without manual bank liaison.'"
        ),
        (
            "Q6. 'What if scammers stop using ATMs and switch to POS machines or Crypto?' (Adversarial Adaptation)",
            "<b>OUR DEFENSE:</b> 'Our candidate retrieval layer is completely polymorphic: the geospatial BallTree index supports POS merchant terminal geometries and crypto exchange on-ramp merchant P2P nodes using the exact same distance and ranking feature space.'"
        ),
        (
            "Q7. 'Is your automated dispatch and tracking legally admissible in court?' (Legal Compliance)",
            "<b>OUR DEFENSE:</b> 'Yes. Every dispatch, acknowledgment, and ML score is hashed using <b>SHA-256</b> and written to an immutable SQLite audit trail table with actor attribution, meeting Section 65B requirements of the Indian Evidence Act for electronic records.'"
        ),
        (
            "Q8. 'Why did you use LightGBM LambdaMART instead of a standard Deep Neural Network?' (Model Justification)",
            "<b>OUR DEFENSE:</b> 'ATM localization is fundamentally a <b>Learning-to-Rank (LTR)</b> problem, not a simple classification task. LambdaMART optimizes directly for NDCG@10 (ranking the true ATM in the top 10), operates at sub-5ms latency on CPUs, and provides complete SHAP tree explainability required for legal and police scrutiny.'"
        )
    ]

    for q_text, ans_text in questions:
        q_card = [
            [Paragraph(q_text, q_title_style)],
            [Paragraph(ans_text, body_style)]
        ]
        t_q = Table(q_card, colWidths=[7.2*inch])
        t_q.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), Q_BG),
            ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#e8c4ad")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_q)
        story.append(Spacer(1, 4))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated Master PDF: {filename}")

if __name__ == '__main__':
    build_pdf("CIRIS_SIH_Judge_Pitch_Deck.pdf")
