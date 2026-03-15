### **XDWe: Teacher-Augmented AI Learning System for Xidian University**

<p style="text-align:center;">XDWe：一个 AI 驱动的师生交流互动平台，实现教学相长</p>

**XDWe** (Xidian + We) is a collaborative, RAG-driven platform designed to transform Xidian University’s academic resources into an intelligent, teacher-verified knowledge network. It empowers students with instant, high-fidelity answers while ensuring educators retain full pedagogical control.

---

## 🛠️ System Architecture & Workflow

To achieve your goal of providing "clear and perfect answers", XDWe operates through a multi-layered verification process. It doesn't just "chat"; it retrieves, validates, and learns from human expertise.

### 1. The Knowledge Injection (RAG)

By populating the `docs/` folder with Markdown files (lecture notes, past exams, wiki docs, or blog posts sharing experiences), you provide the AI with a **Source of Truth**. When a student asks a question, the system performs a semantic search to find the most relevant paragraph from your specific Xidian materials.

### 2. The Teacher-in-the-Loop (Authority)

This is the core of the "XDWe" philosophy. If the AI's answer is good but not "perfect," a teacher can intervene:

* **Submit Authority:** Teachers review student queries and submit an **Authoritative Answer**.
* **Priority Ranking:** The system uses vector similarity to ensure that if a teacher has answered a question, the AI will prioritize that exact text over its own generated response in the future.

### 3. Analytics for Educators

XDWe acts as a diagnostic tool. Through the stats and pending question interfaces, teachers can:

* Identify **knowledge gaps** (which concepts are being asked about most?).
* Monitor **class sentiment** through the integrated messaging system.
* Receive **email alerts** when a student requires human intervention.

---

## 🚀 Quick Start for Teachers

| Task | Action | Result |
| --- | --- | --- |
| **Feed the AI** | Drop `.md` files into the `docs/` folder. | AI learns Xidian-specific course content. |
| **Verify Content** | Use `/api/questions/pending` to review Q&A. | Teachers see what students are curious about. |
| **Set Authority** | Post to `/api/questions/<id>/authoritative`. | The AI adopts the teacher's answer as the "Gold Standard." |