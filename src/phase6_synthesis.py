import os
import re
import shutil
from pathlib import Path

def synthesize_report():
    print("[Step 1] Initializing Synthesis...")
    base_dir = Path("outputs")
    output_dir = base_dir / "phase6"
    img_dir = output_dir / "images"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)
    
    phases = [
        ("Phase 1: Data Acquisition", base_dir / "phase1" / "phase1_report.md"),
        ("Phase 2: Data Structuring", base_dir / "phase2" / "phase2_report.md"),
        ("Phase 3: Objective Weighting", base_dir / "phase3" / "phase3_report.md"),
        ("Phase 4: Transit Suitability Typologies", base_dir / "phase4" / "phase4_report.md"),
        ("Phase 5: Predictive Modeling & Interpretability", base_dir / "phase5" / "phase5_report.md"),
    ]
    
    final_content = []
    final_content.append("# Master Thesis Synthesis: Predictive Transit Site Suitability in ZMG")
    final_content.append("\n## Executive Summary")
    final_content.append("This document synthesizes the five phases of the Node-Place-People-Vitality (NPP-V) predictive framework applied to the Guadalajara Metropolitan Area. It transitions from raw data ingestion to objective weighting, typology discovery, and supervised predictive modeling.")
    
    final_content.append("\n## Table of Contents")
    for title, _ in phases:
        anchor = title.lower().replace(" ", "-").replace(":", "")
        final_content.append(f"- [{title}](#{anchor})")
    
    print("[Step 2] Processing Phase Reports...")
    for title, report_path in phases:
        if not report_path.exists():
            print(f"  [WARN] {report_path} not found. Skipping.")
            continue
            
        print(f"  Processing {title}...")
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract images and copy them
        # Pattern for ![alt](path) or [text](path.png)
        img_pattern = r'(!?\[.*?\]\((.*?\.(?:png|jpg|jpeg|gif))\))'
        matches = re.findall(img_pattern, content)
        
        for full_match, img_rel_path in matches:
            src_img = report_path.parent / img_rel_path
            if src_img.exists():
                dest_img_name = f"{report_path.parent.name}_{img_rel_path.split('/')[-1]}"
                dest_img = img_dir / dest_img_name
                shutil.copy2(src_img, dest_img)
                
                # Update content with new relative path
                new_rel_path = f"images/{dest_img_name}"
                content = content.replace(img_rel_path, new_rel_path)
            else:
                print(f"    [WARN] Image {src_img} not found.")

        # Clean up existing headers to fit hierarchy (shift down)
        content = content.replace("\n# ", "\n### ")
        content = content.replace("\n## ", "\n#### ")
        
        final_content.append(f"\n<a name='{title.lower().replace(' ', '-').replace(':', '')}'></a>")
        final_content.append(f"\n## {title}")
        final_content.append(content)
        final_content.append("\n---\n")

    print("[Step 3] Finalizing Document...")
    final_content.append("\n## Conclusion")
    final_content.append("The NPP-V framework demonstrates a robust, data-driven approach to identifying transit suitability. The integration of unsupervised clustering and supervised interpretability (SHAP) provides both the 'where' and the 'why', offering a scalable methodology for urban transit planning.")
    
    master_path = output_dir / "master_thesis_synthesis.md"
    with open(master_path, "w", encoding="utf-8") as f:
        f.write("\n".join(final_content))
        
    print(f"  [OK] Master report generated at {master_path}")

if __name__ == "__main__":
    synthesize_report()
