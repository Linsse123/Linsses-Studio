import React, { useState } from 'react';
import { ExternalLink, LayoutGrid, Code, FileSpreadsheet, Play, Activity, CheckCircle2, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const NODES_DATA = [
    {
        name: "Configuración",
        type: "Code",
        description: "Nodo inicial que define el entorno (range/test) y las variables globales de la ejecución.",
        code: `return [{ json: { 
  mode: 'range', 
  startDate: '2026-03-01', 
  endDate: '2026-03-11',
  mockBase: 'https://n8n-linssestudio.duckdns.org/webhook' 
} }];`
    },
    {
        name: "CDMX Filter",
        type: "Filter (Nativo)",
        description: "Lógica visual de detección. Valida coordenadas geográficas (Bounding Box) o coincidencia de texto en la dirección.",
        code: "Reglas Visuales:\\n1. Lat: 19.2 - 19.6\\n2. Lon: -99.4 - -98.9\\n3. Texto: contiene 'CDMX' o 'Ciudad de México'"
    },
    {
        name: "Record Mapper",
        type: "Set (Nativo)",
        description: "Mapeo estructurado de 11 columnas para la exportación final. No requiere scripts complejos.",
        code: "Mapeo de Campos:\\n- taskID \u2192 $json.taskID\\n- customerId \u2192 $json.customerId\\n- cityDetected \u2192 'CDMX'\\n- processedAt \u2192 $now.toISO()"
    }
];

function App() {
    const [activeTab, setActiveTab] = useState('monitor');
    const [selectedNode, setSelectedNode] = useState(0);

    const n8nUrl = "https://n8n-linssestudio.duckdns.org/workflow/MIqelspKYbVDZGrm";
    const sheetsUrl = "https://docs.google.com/spreadsheets/d/1lwYeT9iocQRlP3H_54RdPTq2F2lq4M2x1hurKD_pcfE";

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-[#ededed] p-4 md:p-8 font-sans">
            <header className="max-w-7xl mx-auto mb-12 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                    <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent mb-2">
                        Pipeline CDMX
                    </h1>
                    <p className="text-[#ededed]/60 text-lg flex items-center gap-2">
                        <Activity className="w-4 h-4 text-emerald-400" />
                        Centro de Monitoreo de Procesamiento | n8n v2.9.2
                    </p>
                </motion.div>

                <nav className="flex items-center gap-2 p-1 bg-white/5 rounded-2xl border border-white/5 backdrop-blur-md">
                    <TabButton active={activeTab === 'monitor'} onClick={() => setActiveTab('monitor')} icon={<LayoutGrid className="w-4 h-4" />} label="Monitor" />
                    <TabButton active={activeTab === 'code'} onClick={() => setActiveTab('code')} icon={<Code className="w-4 h-4" />} label="Inspector" />
                </nav>
            </header>

            <main className="max-w-7xl mx-auto">
                <AnimatePresence mode="wait">
                    {activeTab === 'monitor' ? (
                        <motion.div key="monitor" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                            <div className="lg:col-span-2 space-y-6">
                                <div className="relative aspect-video bg-white/5 rounded-3xl overflow-hidden border border-white/5 group backdrop-blur-sm">
                                    <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/20 transition-all z-10">
                                        <a href={n8nUrl} target="_blank" rel="noreferrer" className="px-8 py-4 bg-blue-500 hover:bg-blue-600 text-white rounded-full font-bold flex items-center gap-3 shadow-2xl transition-transform active:scale-95">
                                            <Play className="w-5 h-5 fill-current" />
                                            Acceder a n8n Live
                                            <ExternalLink className="w-4 h-4" />
                                        </a>
                                    </div>
                                    <div className="w-full h-full flex items-center justify-center border-2 border-dashed border-white/10 italic text-white/20">
                                        Sincronización con n8n establecida
                                    </div>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <QuickStat icon={<CheckCircle2 className="text-emerald-400" />} label="Estatus" value="Operativo" />
                                    <QuickStat icon={<Activity className="text-blue-400" />} label="Tareas/Lote" value="50 items" />
                                </div>
                            </div>

                            <div className="space-y-6">
                                <div className="bg-white/5 border border-white/5 p-8 rounded-3xl space-y-6 backdrop-blur-md">
                                    <h3 className="text-2xl font-bold flex items-center gap-3">
                                        <FileSpreadsheet className="text-emerald-400" />
                                        Resultados Finales
                                    </h3>
                                    <p className="text-[#ededed]/60 leading-relaxed">
                                        Visualiza la exportación de las 11 columnas procesadas en tiempo real dentro de Google Sheets.
                                    </p>
                                    <a href={sheetsUrl} target="_blank" rel="noreferrer" className="block p-6 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-2xl text-emerald-400 font-bold text-center transition-all group">
                                        Ver Google Sheets
                                        <ChevronRight className="inline ml-2 group-hover:translate-x-1 transition-transform" />
                                    </a>
                                </div>
                            </div>
                        </motion.div>
                    ) : (
                        <motion.div key="code" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="grid grid-cols-1 md:grid-cols-4 gap-8">
                            <div className="space-y-4">
                                {NODES_DATA.map((node, idx) => (
                                    <button key={node.name} onClick={() => setSelectedNode(idx)} className={`w-full text-left p-6 rounded-2xl border transition-all ${selectedNode === idx ? 'bg-blue-500/10 border-blue-500 text-blue-400' : 'bg-white/5 border-white/5 hover:border-white/10'}`}>
                                        <div className="font-bold mb-1">{node.name}</div>
                                        <div className="text-xs opacity-60 uppercase tracking-tighter">{node.type}</div>
                                    </button>
                                ))}
                            </div>
                            <div className="md:col-span-3 bg-white/5 border border-white/5 p-8 rounded-3xl space-y-8 backdrop-blur-md">
                                <div>
                                    <h2 className="text-3xl font-bold mb-4">{NODES_DATA[selectedNode].name}</h2>
                                    <p className="text-[#ededed]/60 text-lg">{NODES_DATA[selectedNode].description}</p>
                                </div>
                                <div className="bg-black/50 p-6 rounded-2xl font-mono text-sm border border-white/5 overflow-x-auto whitespace-pre leading-relaxed text-blue-300">
                                    {NODES_DATA[selectedNode].code}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>
            <footer className="mt-20 py-10 border-t border-white/5 text-center text-[#ededed]/20 text-xs tracking-[0.2em] font-medium font-sans">
                ENTREGA TÉCNICA | PAQUETECDMX | 2026
            </footer>
        </div>
    );
}

function TabButton({ active, onClick, icon, label }: any) {
    return (
        <button onClick={onClick} className={`px-6 py-3 rounded-xl flex items-center gap-3 transition-all font-medium ${active ? 'bg-white/10 text-white shadow-lg' : 'text-white/40 hover:text-white/60 hover:bg-white/5'}`}>
            {icon} {label}
        </button>
    );
}

function QuickStat({ icon, label, value }: any) {
    return (
        <div className="bg-white/5 border border-white/5 p-6 rounded-2xl flex items-center gap-5 backdrop-blur-sm">
            <div className="p-3 bg-white/5 rounded-xl">{icon}</div>
            <div>
                <div className="text-xs text-[#ededed]/40 uppercase font-bold tracking-wider">{label}</div>
                <div className="text-xl font-bold">{value}</div>
            </div>
        </div>
    );
}

export default App;
