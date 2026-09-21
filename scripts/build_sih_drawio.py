"""
Script to generate the updated draw.io XML for Sentinel AI system workflow:
- Correct model names from repo (Qwen router, Qwen3-VL-4B, DeepSeek-R1-7B, Qwen2.5-Coder-7B, nomic-embed-text)
- AI Orchestrator explicitly identified as Qwen model
- Pure CLI Workbench (TUI) - NO Web UI
- NO system/hardware config (no RTX 2050, 4GB VRAM, psutil, IP addresses)
- Clean, end-to-end Context Summarization & Chat Reset workflow
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

def generate_drawio_xml():
    mxfile = ET.Element("mxfile", {
        "host": "app.diagrams.net",
        "modified": "2026-09-19T00:00:00.000Z",
        "agent": "Antigravity",
        "version": "24.0.0",
        "type": "device"
    })
    
    diagram = ET.SubElement(mxfile, "diagram", {
        "id": "sentinel-ai-workflow",
        "name": "Sentinel AI – System Workflow"
    })
    
    graph_model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1800",
        "dy": "2400",
        "grid": "1",
        "gridSize": "10",
        "guides": "1",
        "tooltips": "1",
        "connect": "1",
        "arrows": "1",
        "fold": "1",
        "page": "1",
        "pageScale": "1",
        "pageWidth": "1654",
        "pageHeight": "2339",
        "math": "0",
        "shadow": "1"
    })
    
    root = ET.SubElement(graph_model, "root")
    
    # Base cells
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    
    def add_cell(cell_id, value, style, x, y, width, height, parent="1", is_vertex=True):
        cell = ET.SubElement(root, "mxCell", {
            "id": cell_id,
            "value": value,
            "style": style,
            "parent": parent,
            "vertex": "1" if is_vertex else "0"
        })
        if x is not None and y is not None:
            ET.SubElement(cell, "mxGeometry", {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "as": "geometry"
            })
        return cell

    def add_edge(edge_id, source, target, style, value="", points=None):
        edge = ET.SubElement(root, "mxCell", {
            "id": edge_id,
            "value": value,
            "style": style,
            "parent": "1",
            "edge": "1",
            "source": source,
            "target": target
        })
        geom = ET.SubElement(edge, "mxGeometry", {
            "relative": "1",
            "as": "geometry"
        })
        if points:
            arr = ET.SubElement(geom, "Array", {"as": "points"})
            for px, py in points:
                ET.SubElement(arr, "mxPoint", {"x": str(px), "y": str(py)})
        return edge

    # Styles matching original flowchart colors
    CARD_BASE = "rounded=1;whiteSpace=wrap;html=1;arcSize=18;strokeWidth=2;fontFamily=Helvetica;align=center;"
    STYLE_USER = CARD_BASE + "fillColor=#d5e8d4;strokeColor=#82b366;fontColor=#1b4332;"
    STYLE_TUI = CARD_BASE + "fillColor=#dae8fc;strokeColor=#6c8ebf;fontColor=#1e3a8a;"
    STYLE_ORCH = CARD_BASE + "fillColor=#e1d5e7;strokeColor=#9673a6;fontColor=#3c096c;"
    STYLE_ROUTER = CARD_BASE + "fillColor=#ffe6cc;strokeColor=#d6b656;fontColor=#78350f;"
    
    STYLE_SPEC_DOC = CARD_BASE + "fillColor=#dae8fc;strokeColor=#6c8ebf;fontColor=#1e3a8a;"
    STYLE_SPEC_VIS = CARD_BASE + "fillColor=#d5e8d4;strokeColor=#82b366;fontColor=#1b4332;"
    STYLE_SPEC_REAS = CARD_BASE + "fillColor=#fff2cc;strokeColor=#d6b656;fontColor=#78350f;"
    STYLE_SPEC_RAG = CARD_BASE + "fillColor=#f8cecc;strokeColor=#b85450;fontColor=#7f1d1d;"
    
    STYLE_TOOLS = CARD_BASE + "fillColor=#dae8fc;strokeColor=#6c8ebf;fontColor=#1e3a8a;"
    STYLE_RESULTS = CARD_BASE + "fillColor=#e1d5e7;strokeColor=#9673a6;fontColor=#3c096c;"
    STYLE_MEMORY = CARD_BASE + "fillColor=#d5e8d4;strokeColor=#82b366;fontColor=#1b4332;"
    
    CALLOUT_STYLE = "rounded=1;whiteSpace=wrap;html=1;arcSize=10;dashed=1;fillColor=#f8fafc;strokeColor=#94a3b8;strokeWidth=1.5;fontFamily=Helvetica;align=left;spacingLeft=10;spacingTop=6;spacingBottom=6;spacingRight=10;verticalAlign=top;fontColor=#334155;"
    
    ARROW_MAIN = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#1e293b;strokeWidth=2;endArrow=classic;endFill=1;"
    ARROW_DASH = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#64748b;strokeWidth=1.5;dashed=1;endArrow=none;"
    ARROW_LOOP = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#2563eb;strokeWidth=2;dashed=1;endArrow=classic;endFill=1;fontColor=#1e40af;fontSize=11;fontStyle=1;"

    # 1. HEADER (No system config)
    add_cell("hdr_banner", 
             '<b style="font-size: 20px;">Sentinel AI — System Workflow</b><br/>'
             '<span style="font-size: 12px; color: #475569;">End-to-End Autonomous Agent Execution &amp; Context Lifecycle</span>',
             "rounded=1;whiteSpace=wrap;html=1;fillColor=#f1f5f9;strokeColor=#cbd5e1;strokeWidth=1.5;align=center;arcSize=12;fontFamily=Helvetica;",
             220, 20, 780, 50)

    # 2. MAIN PROCESS NODES (CENTER COLUMN: X=320, W=420)
    # Node 1: User
    add_cell("node_user",
             '<b style="font-size: 14px;">User</b><br/>'
             '<span style="font-size: 11px;">Engineer / Operator / Technical Staff</span>',
             STYLE_USER, 320, 95, 420, 55)
    
    # Callout 1: Input
    add_cell("callout_input",
             '<b style="font-size: 11px; color: #0f172a;">Input</b><br/>'
             '• Natural language query<br/>'
             '• Documents / Images / Files<br/>'
             '• Tasks / Reports / Analysis',
             CALLOUT_STYLE, 780, 85, 270, 75)
    add_edge("e_c1", "node_user", "callout_input", ARROW_DASH)

    # Node 2: CLI Workbench (TUI) - NO Web UI
    add_cell("node_tui",
             '<b style="font-size: 14px;">CLI Workbench (TUI)</b><br/>'
             '<span style="font-size: 11px;">Built with Python + Textual + Rich</span>',
             STYLE_TUI, 320, 190, 420, 55)
    add_edge("arr_1_2", "node_user", "node_tui", ARROW_MAIN)

    # Callout 2: User Interface
    add_cell("callout_ui",
             '<b style="font-size: 11px; color: #0f172a;">User Interface</b><br/>'
             '• Interactive CLI terminal (Textual)<br/>'
             '• Real-time streaming output<br/>'
             '• File upload &amp; task management',
             CALLOUT_STYLE, 780, 180, 270, 75)
    add_edge("e_c2", "node_tui", "callout_ui", ARROW_DASH)

    # Node 3: AI Orchestrator (Qwen Model)
    add_cell("node_orch",
             '<b style="font-size: 14px;">AI Orchestrator (Qwen)</b><br/>'
             '<span style="font-size: 11px;">Custom MasterAgent (Asyncio) · Qwen Model</span>',
             STYLE_ORCH, 320, 285, 420, 55)
    add_edge("arr_2_3", "node_tui", "node_orch", ARROW_MAIN)

    # Callout 3: Task Planning
    add_cell("callout_orch",
             '<b style="font-size: 11px; color: #0f172a;">Task Planning</b><br/>'
             '• Decompose task into subtasks<br/>'
             '• Coordinate specialist agents<br/>'
             '• Manage context &amp; memory',
             CALLOUT_STYLE, 780, 275, 270, 75)
    add_edge("e_c3", "node_orch", "callout_orch", ARROW_DASH)

    # Node 4: Task Understanding & Routing (No system config)
    add_cell("node_router",
             '<b style="font-size: 14px;">Task Understanding &amp; Routing</b><br/>'
             '<span style="font-size: 11px;">YAML Model Registry · Ollama Backend</span>',
             STYLE_ROUTER, 320, 380, 420, 55)
    add_edge("arr_3_4", "node_orch", "node_router", ARROW_MAIN)

    # Callout 4: Model Router
    add_cell("callout_router",
             '<b style="font-size: 11px; color: #0f172a;">Model Router</b><br/>'
             '• Select best model for task<br/>'
             '• Load / unload on demand<br/>'
             '• Optimize execution pipeline',
             CALLOUT_STYLE, 780, 370, 270, 75)
    add_edge("e_c4", "node_router", "callout_router", ARROW_DASH)

    # 3. SPECIALIST AGENTS ROW (Actual model names from repo)
    # Box 1: Document Agent
    add_cell("agent_doc",
             '<b style="font-size: 12px;">Document Agent</b><br/>'
             '<span style="font-size: 10px;">PDFs, Docs, Sheets, OCR<br/>(pdfplumber, PyPDF2, Tesseract)</span>',
             STYLE_SPEC_DOC, 75, 475, 210, 70)

    # Box 2: Vision Agent
    add_cell("agent_vis",
             '<b style="font-size: 12px;">Vision Agent</b><br/>'
             '<span style="font-size: 10px;">Images, Diagrams, OCR<br/>(Qwen3-VL-4B)</span>',
             STYLE_SPEC_VIS, 300, 475, 210, 70)

    # Box 3: Reasoning / Coding Agent
    add_cell("agent_reas",
             '<b style="font-size: 12px;">Reasoning / Coding Agent</b><br/>'
             '<span style="font-size: 10px;">DeepSeek-R1-7B,<br/>Qwen2.5-Coder-7B</span>',
             STYLE_SPEC_REAS, 525, 475, 210, 70)

    # Box 4: Embedding & RAG
    add_cell("agent_rag",
             '<b style="font-size: 12px;">Embedding &amp; RAG</b><br/>'
             '<span style="font-size: 10px;">nomic-embed-text<br/>+ ChromaDB</span>',
             STYLE_SPEC_RAG, 750, 475, 210, 70)

    # Router to 4 Specialists
    add_edge("e_r_doc", "node_router", "agent_doc", ARROW_MAIN)
    add_edge("e_r_vis", "node_router", "agent_vis", ARROW_MAIN)
    add_edge("e_r_reas", "node_router", "agent_reas", ARROW_MAIN)
    add_edge("e_r_rag", "node_router", "agent_rag", ARROW_MAIN)

    # 4. TOOLS, EXECUTION & RESULTS (CENTER COLUMN - No system config)
    # Node 5: Tool Execution & Sandbox
    add_cell("node_tools",
             '<b style="font-size: 14px;">Tool Execution &amp; Sandbox</b><br/>'
             '<span style="font-size: 11px;">ToolRegistry + ReAct | Docker (Isolated) | Network Guard</span>',
             STYLE_TOOLS, 210, 580, 640, 55)
    
    # 4 Specialists to Tools
    add_edge("e_doc_t", "agent_doc", "node_tools", ARROW_MAIN)
    add_edge("e_vis_t", "agent_vis", "node_tools", ARROW_MAIN)
    add_edge("e_reas_t", "agent_reas", "node_tools", ARROW_MAIN)
    add_edge("e_rag_t", "agent_rag", "node_tools", ARROW_MAIN)

    # Node 6: Result Generation
    add_cell("node_results",
             '<b style="font-size: 14px;">Result Generation</b><br/>'
             '<span style="font-size: 11px;">Answer, Analysis, Report, Charts, Files</span>',
             STYLE_RESULTS, 210, 670, 640, 55)
    add_edge("arr_5_6", "node_tools", "node_results", ARROW_MAIN)

    # Callout 5: Outputs
    add_cell("callout_outputs",
             '<b style="font-size: 11px; color: #0f172a;">Outputs</b><br/>'
             '• Text / Reports / Charts<br/>'
             '• Generated files<br/>'
             '• Actionable insights',
             CALLOUT_STYLE, 880, 660, 260, 75)
    add_edge("e_c5", "node_results", "callout_outputs", ARROW_DASH)

    # Node 7: Workspace & Memory
    add_cell("node_memory",
             '<b style="font-size: 14px;">Workspace &amp; Memory</b><br/>'
             '<span style="font-size: 11px;">SQLite (sessions.db) + ChromaDB + Local File System</span>',
             STYLE_MEMORY, 210, 760, 640, 55)
    add_edge("arr_6_7", "node_results", "node_memory", ARROW_MAIN)

    # Callout 6: Persistence
    add_cell("callout_persist",
             '<b style="font-size: 11px; color: #0f172a;">Persistence</b><br/>'
             '• Conversation history<br/>'
             '• Session checkpoints<br/>'
             '• Generated artifacts &amp; logs',
             CALLOUT_STYLE, 880, 750, 260, 75)
    add_edge("e_c6", "node_memory", "callout_persist", ARROW_DASH)

    # =========================================================================
    # 5. CONTEXT WINDOW MANAGEMENT & SUMMARIZATION FLOW
    # =========================================================================
    add_cell("group_context",
             "CONTEXT WINDOW MANAGEMENT &amp; SUMMARIZATION",
             "swimlane;whiteSpace=wrap;html=1;fillColor=#f8fafc;strokeColor=#475569;strokeWidth=1.5;dashed=1;fontColor=#1e293b;fontFamily=Helvetica;fontSize=12;fontStyle=1;startSize=28;arcSize=10;",
             60, 855, 1100, 310)

    # Decision Diamond: Context Limit Check
    add_cell("dec_context",
             '<b style="font-size: 12px;">Context Limit<br/>Reached?</b>',
             "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;strokeWidth=2;fontFamily=Helvetica;align=center;fontColor=#78350f;",
             435, 915, 190, 85)
    
    add_edge("e_mem_dec", "node_memory", "dec_context", ARROW_MAIN)

    # [NO] Branch: Normal chat continuation loop-back
    add_edge("e_dec_no", "dec_context", "node_user", 
             ARROW_LOOP + "labelBackgroundColor=#ffffff;", 
             value="[NO] Normal Chat Continues",
             points=[(180, 957), (180, 122)])

    # [YES] Branch: Context Summarization Sub-Pipeline
    # Step A: Summarization Engine (Qwen)
    add_cell("step_summary",
             '<b style="font-size: 12px;">1. Summarise Current Chat (Qwen)</b><br/>'
             '<span style="font-size: 10px;">Generates concise summary of dialogue, key decisions &amp; findings</span>',
             STYLE_ORCH, 700, 895, 420, 65)
    
    add_edge("e_dec_yes", "dec_context", "step_summary", 
             ARROW_MAIN + "strokeColor=#dc2626;fontColor=#dc2626;fontStyle=1;", 
             value="[YES: Limit Reached]")

    # Step B: Archive Old Session
    add_cell("step_archive",
             '<b style="font-size: 12px;">2. Archive Current Chat</b><br/>'
             '<span style="font-size: 10px;">Full transcript committed to SQLite (sessions.db) &amp; archived</span>',
             STYLE_TUI, 700, 980, 420, 60)
    
    add_edge("e_sum_arch", "step_summary", "step_archive", ARROW_MAIN)

    # Step C: Initialize New Session with Summary
    add_cell("step_new_chat",
             '<b style="font-size: 12px;">3. Start New Chat Session</b><br/>'
             '<span style="font-size: 10px;">Starts clean chat session with previous Context Summary injected</span>',
             STYLE_USER, 700, 1060, 420, 65)
    
    add_edge("e_arch_new", "step_archive", "step_new_chat", ARROW_MAIN)

    # Edge from New Chat Session back to Orchestrator
    add_edge("e_new_to_orch", "step_new_chat", "node_orch",
             ARROW_LOOP + "strokeColor=#059669;fontColor=#047857;labelBackgroundColor=#ffffff;",
             value="Injects Context Summary & Continues Seamlessly",
             points=[(1140, 1092), (1140, 312)])

    # Continuous Interaction label on the far left
    add_cell("lbl_cont_left",
             '<b style="font-size: 11px; color: #1e40af;">Continuous<br/>Interaction</b>',
             "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;rotation=-90;",
             100, 350, 110, 40)

    # Color Legend at bottom
    add_cell("legend_banner",
             '<span style="font-size: 10px; color: #475569;">'
             '<b>Legend:</b> '
             '<span style="background-color:#d5e8d4; padding:2px 8px; border-radius:4px; border:1px solid #82b366;">User &amp; Memory</span> &nbsp; '
             '<span style="background-color:#dae8fc; padding:2px 8px; border-radius:4px; border:1px solid #6c8ebf;">Interface &amp; Tools</span> &nbsp; '
             '<span style="background-color:#e1d5e7; padding:2px 8px; border-radius:4px; border:1px solid #9673a6;">AI Orchestrator &amp; Results</span> &nbsp; '
             '<span style="background-color:#ffe6cc; padding:2px 8px; border-radius:4px; border:1px solid #d6b656;">Model Routing</span> &nbsp; '
             '<span style="background-color:#fff2cc; padding:2px 8px; border-radius:4px; border:1px solid #d6b656;">Decision Point</span>'
             '</span>',
             "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#cbd5e1;strokeWidth=1;align=center;fontFamily=Helvetica;",
             220, 1185, 780, 35)

    # Output XML string
    xml_bytes = ET.tostring(mxfile, encoding="utf-8")
    parsed = minidom.parseString(xml_bytes)
    return parsed.toprettyxml(indent="  ")

if __name__ == "__main__":
    content = generate_drawio_xml()
    out_path = "d:/SIH2026/PS1/New folder/sih_workflow_with_context_summary.drawio"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully generated drawio file at: {out_path}")
