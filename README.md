# TimableV2 - Smart Timetable Builder

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/streamlit-1.28%2B-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![OR-Tools](https://img.shields.io/badge/OR--Tools-9.5%2B-4285F4?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/license-Apache--2.0-green?style=for-the-badge)
![Status](https://img.shields.io/badge/status-production-success?style=for-the-badge)

### **An intelligent, animated school timetable generator**
**Powered by constraint programming • Built with love for educators**

*Smooth • Stable • Alive*

[ Quick Start](#-quick-start) • [ Features](#-features) • [Documentation](#-documentation) • [ Demo](#-demo-data)

</div>

---

## 📋 Overview

**TimableV2** is a next-generation school scheduling solution that transforms complex timetable creation into an elegant, visual experience. Combining **Google's OR-Tools constraint solver** with a **beautifully animated dark-themed interface**, it generates mathematically guaranteed clash-free schedules with real-time analytics, scenario simulation, and stunning visualizations.

### Why TimableV2?

| Intelligent | Beautiful | Analytical |
|-------------|------------|------------|
| Constraint programming ensures zero conflicts | Fluid animations, glowing transitions, modern dark theme | Visual heatmaps and energy fields reveal insights at a glance |

### Key Highlights

- ✅ **Zero Conflicts Guaranteed** - Mathematical proof via constraint programming
- ✅ **5 What-If Scenarios** - Test disruptions without touching base timetable
- ✅ **8 Visual Analytics** - Heatmaps + Teacher networks + Load balancing
- ✅ **Subject Prerequisites** - Enforce sequencing between subjects
- ✅ **Teacher Preferences** - Availability and preferred periods
- ✅ **Elective Management** - Optional subjects for students
- ✅ **Auto-Save Everything** - JSON persistence across sessions
- ✅ **Professional PDFs** - Print-ready A4 landscape exports
- ✅ **Desktop App Ready** - Windows installer included

---

## 🚀 Features

### Core Scheduling Engine

| Feature | Description |
|---------|-------------|
| Clash-Free Generation | No teacher or class double-booking (hard constraint) |
| Priority Scheduling | Important subjects scheduled earlier in the day |
| Teacher Constraints | Respect max periods per day + max periods per week |
| Break Periods | Configurable breaks (Lunch, Tea, etc.) |
| Weekly Rotation | 3-week automatic rotation for fairness |
| OR-Tools Solver | Google's constraint programming solver (CP-SAT) |

### Advanced Features

| Feature | Description |
|---------|-------------|
| **Constraint Management** | Auto-detects and resolves teacher overload |
| **Teacher Preferences** | Preferred/unavailable periods per teacher |
| **Subject Prerequisites** | Enforce subject sequencing (e.g., Math → Physics) |
| **Max Consecutive Periods** | Prevent teacher overload with gap enforcement |
| **Load Balancing** | Even distribution of periods across days |
| **Shared Teacher Analysis** | Visual breakdown of multi-class teachers |
| **Elective Management** | Define elective groups and selections |

### Visual Analytics

- **Heatmaps** - Teacher load, day congestion, class fatigue, clash risk
- **Teacher Networks** - Graph visualization of teacher-class connections
- **Load Balancing Dashboard** - Period distribution per teacher per day

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Nayak-indie/TimableV2.git
cd TimableV2

# Create conda environment (recommended)
conda create -n timable python=3.11
conda activate timable

# Install dependencies
pip install -r requirements.txt
```

## ▶️ Run Application

```bash
streamlit run app.py
```

Application opens at: **http://localhost:8510**

---

## 📚 Documentation

### Sidebar Configuration

```yaml
Days: Mon, Tue, Wed, Thu, Fri
Periods per day: 8
Break Periods:
  4: Lunch
```

### 8-Tab Interface

1. **Teachers & Classes** - Add/manage teachers, classes, subjects
2. **Class Timetables** - Generate and view class schedules
3. **Teacher Timetables** - Generate and view teacher schedules
4. **Connections** - Teacher-class network visualization
5. **Heatmaps** - Visual analytics
6. **PDF Export** - Download printable schedules
7. **History** - Activity log
8. **Electives** - Manage optional subjects

---

## 📊 Demo Data

### Teachers (15 Total)

Science: Eric Simon (Physics), Aisha Khan (Chemistry), Rahul Mehta (Math), Neha Verma (Biology)

Commerce: Priya Nair (Economics), Arjun Patel (Accountancy), Kavita Rao (Business Studies)

Humanities: Sofia Mendes (History), Aman Gupta (Political Science), Ritu Chawla (Geography)

Common: Daniel Brooks, Sarah John (English), Marcus Lee, Mike Johnson (PE), Rashmi Joshi, Deepa Patel (Hindi), Vikram Singh (Computer Science), Anjali Roy (Art)

### Classes (9 Total)

- 11NM, 11M, 11COM, 11HUM (Class 11)
- 12SCI, 12COM, 12HUM, 11CS, 12CS (Class 12)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Solver | OR-Tools CP-SAT |
| Visualization | Plotly, Matplotlib |
| Data | Pandas, NumPy |
| PDF | ReportLab |
| Storage | JSON |

---

## 📄 License

Licensed under **Apache License 2.0** - See [LICENSE](LICENSE) file.

---

## 🤝 Contributing

Contributions welcome! Open an issue or submit a PR.

---

## 📧 Contact

[GitHub Issues](https://github.com/Nayak-indie/TimableV2/issues)

---

<div align="center">

**Made with Python, Streamlit, and OR-Tools**

</div>
