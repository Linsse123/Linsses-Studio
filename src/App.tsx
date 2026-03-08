```javascript
import React, { useState } from 'react';
import { ExternalLink, LayoutGrid, Code, FileSpreadsheet, Play, Activity, CheckCircle2, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const NODES_DATA = [
  {
    id: "config",
    name: "Configuración",
    type: "Code",
    description: "Define el entorno y variables globales.",
    code: `return [{ json: { mode: 'range', startDate: '2026-03-01', endDate: '2026-03-11' } }]; `
  },
  {
    id: "fetch",
    name: "Get Tasks",
    type: "HTTP Request",
    description: "Obtiene las tareas pendientes desde el Mock API.",
    code: "GET {{ $node[\"Configuración\"].json[\"mockBase\"] }}/tasks"
  },
  {
    id: "filter",
    name: "CDMX Filter",
    type: "Filter",
    description: "Valida coordenadas y texto para detectar Ciudad de México.",
    code: "Reglas: Lat (19.2-19.6), Lon (-99.4--98.9) OR Text (CDMX)"
  },
  {
    id: "sheets",
    name: "Google Sheets",
    type: "Google Sheets",
    description: "Exportación final de las 11 columnas procesadas.",
    code: "Operación: Append | Sheet: Resultados_CDMX"
  }
];

function App() {
    const [activeTab, setActiveTab] = useState('monitor');
    const [selectedNode, setSelectedNode] = useState(0);
    const [isExecuting, setIsExecuting] = useState(false);
    const [executionStep, setExecutionStep] = useState(-1);

    const n8nUrl = "https://n8n-linssestudio.duckdns.org/workflow/MIqelspKYbVDZGrm";
    const sheetsUrl = "https://docs.google.com/spreadsheets/d/1lwYeT9iocQRlP3H_54RdPTq2F2lq4M2x1hurKD_pcfE";
    const webhookUrl = "https://n8n-linssestudio.duckdns.org/webhook/df784b8d-638e-4a6c-9404-5868fa05ed92"; // URL de ejemplo para el webhook

    const handleExecute = async () => {
      setIsExecuting(true);
      setExecutionStep(0);
      
      // Simulación visual de pasos
      for (let i = 0; i < NODES_DATA.length; i++) {
        setExecutionStep(i);
        await new Promise(r => setTimeout(r, 1500));
      }
      
      // Intento de disparo real del webhook
      try {
        await fetch(webhookUrl, { method: 'POST', body: JSON.stringify({ trigger: 'web-dashboard' }) });
      } catch (e) {
        console.log("Webhook disparado (CORS prevent browser read, but request sent)");
      }
      
      setIsExecuting(false);
      setExecutionStep(-1);
    };

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-[#ededed] p-4 md:p-8 font-sans transition-colors duration-500">
            <header className="max-w-7xl mx-auto mb-12 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                    <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400 bg-clip-text text-transparent mb-2">
                        Pipeline CDMX
                    </h1>
                    <p className="text-[#ededed]/60 text-lg flex items-center gap-2">
                        <Activity className={`w - 4 h - 4 ${ isExecuting ? 'animate-pulse text-emerald-400' : 'text-foreground/40' } `} />
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
                                {/* Visual Frame Simulation */}
                                <div className="glass p-8 rounded-3xl border border-white/10 relative overflow-hidden h-[400px] flex flex-col justify-center">
                                  <div className="absolute top-4 left-6 flex items-center gap-2">
                                    <div className={`w - 2 h - 2 rounded - full ${ isExecuting ? 'bg-emerald-400 animate-ping' : 'bg-white/20' } `} />
                                    <span className="text-[10px] uppercase tracking-widest font-bold opacity-40">Live Workflow Simulation</span>
                                  </div>
                                  
                                  <div className="flex flex-wrap items-center justify-center gap-8 relative z-10">
                                    {NODES_DATA.map((node, i) => (
                                      <React.Fragment key={node.id}>
                                        <motion.div 
                                          animate={{ 
                                            scale: executionStep === i ? 1.1 : 1,
                                            borderColor: executionStep === i ? '#3b82f6' : 'rgba(255,255,255,0.1)',
                                            backgroundColor: executionStep === i ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.05)'
                                          }}
                                          className="w-32 h-32 rounded-2xl border-2 flex flex-col items-center justify-center gap-2 text-center p-2 relative shadow-2xl"
                                        >
                                          {i === 0 ? <Activity className="w-6 h-6 text-blue-400" /> : 
                                           i === 1 ? <Play className="w-6 h-6 text-emerald-400" /> :
                                           i === 2 ? <LayoutGrid className="w-6 h-6 text-amber-400" /> :
                                           <FileSpreadsheet className="w-6 h-6 text-emerald-500" />}
                                          <span className="text-[10px] font-bold uppercase leading-tight">{node.name}</span>
                                          {executionStep === i && (
                                            <motion.div layoutId="glow" className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full -z-10" />
                                          )}
                                        </motion.div>
                                        {i < NODES_DATA.length - 1 && (
                                          <div className={`w - 8 h - 0.5 ${ executionStep > i ? 'bg-emerald-400' : 'bg-white/10' } transition - colors duration - 500`} />
                                        )}
                                      </React.Fragment>
                                    ))}
                                  </div>

                                  <div className="absolute border-t border-white/5 bottom-0 left-0 right-0 p-6 flex items-center justify-between backdrop-blur-xl">
                                    <button 
                                      onClick={handleExecute}
                                      disabled={isExecuting}
                                      className={`px - 8 py - 3 rounded - xl font - bold flex items - center gap - 3 transition - all ${
    isExecuting
        ? 'bg-white/10 text-white/40 cursor-not-allowed'
        : 'bg-emerald-500 hover:bg-emerald-400 text-black shadow-lg shadow-emerald-500/20 active:scale-95'
} `}
                                    >
                                      {isExecuting ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                                      {isExecuting ? 'Ejecutando...' : 'Ejecutar Pipeline'}
                                    </button>

                                    <div className="flex gap-4">
                                      <a href={n8nUrl} target="_blank" rel="noreferrer" className="text-xs text-white/40 hover:text-white flex items-center gap-1 transition-colors">
                                        n8n Workspace <ExternalLink className="w-3 h-3" />
                                      </a>
                                    </div>
                                  </div>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                  <QuickStat icon={<CheckCircle2 className="text-emerald-400" />} label="Estatus" value={isExecuting ? "Procesando" : "En Espera"} />
                                  <QuickStat icon={<Activity className="text-blue-400" />} label="Última Ejecución" value={isExecuting ? "Ahora" : "Hace 5 min"} />
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
                                    <button key={node.name} onClick={() => setSelectedNode(idx)} className={`w - full text - left p - 6 rounded - 2xl border transition - all ${ selectedNode === idx ? 'bg-blue-500/10 border-blue-500 text-blue-400' : 'bg-white/5 border-white/5 hover:border-white/10' } `}>
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
        <button onClick={onClick} className={`px - 6 py - 3 rounded - xl flex items - center gap - 3 transition - all font - medium ${ active ? 'bg-white/10 text-white shadow-lg' : 'text-white/40 hover:text-white/60 hover:bg-white/5' } `}>
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
