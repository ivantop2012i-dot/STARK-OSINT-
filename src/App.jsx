import React, { useState, useEffect } from 'react';
import ReactFlow, { Background } from 'reactflow';
import 'reactflow/dist/style.css';
import { Send, History, X, HelpCircle } from 'lucide-react';

// --- КАСТОМНАЯ КАРТОЧКА ---
const CustomCardNode = ({ data }) => {
  return (
    <div className="bg-[#161616] border border-[#2a2a2a] rounded-2xl p-5 w-[340px] shadow-2xl text-white animate-fade-in">
      <div className="flex justify-between items-center mb-1">
        <h3 className="font-semibold text-[15px]">{data.title}</h3>
      </div>
      {data.status && (
        <div className={`text-[13px] mb-3 ${data.statusColor === 'green' ? 'text-green-500' : data.statusColor === 'red' ? 'text-red-500' : 'text-gray-400'}`}>
          {data.status}
        </div>
      )}
      <div className="text-[12px] space-y-2 text-[#888888] mt-2">
        {data.info && Object.entries(data.info).map(([key, val]) => (
          <div key={key} className="flex justify-between border-b border-[#222] pb-2">
            <span>{key}</span>
            <span className="text-[#cccccc] text-right max-w-[180px] truncate">{val}</span>
          </div>
        ))}
      </div>
      {data.links && (
        <div className="mt-4 space-y-2">
          {data.links.map((link, idx) => (
            <a key={idx} href={link.url} target="_blank" rel="noreferrer" 
               className="flex items-center gap-3 bg-[#1e1e1e] hover:bg-[#252525] p-2.5 rounded-xl text-[12px] transition border border-[#2a2a2a]">
              <span className="w-5 h-5 bg-[#333] rounded-full flex items-center justify-center text-[10px] text-white">i</span>
              <span className="flex-1 text-[#dddddd]">{link.name}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
};
const nodeTypes = { card: CustomCardNode };

export default function App() {
  const [query, setQuery] = useState('');
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/history');
      const data = await res.json();
      setHistory(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleSearch = async (searchQuery = query) => {
    if (!searchQuery) return;
    setLoading(true);
    setQuery(searchQuery);
    setShowHistory(false);
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, type: 'auto' })
      });
      const data = await res.json();
      
      const formattedNodes = data.nodes.map(n => {
        if (n.id === 'root') return { ...n, position: { x: 0, y: 0 }, style: { background: '#161616', color: '#fff', border: '1px solid #333', borderRadius: '24px', padding: '12px 24px', fontSize: '14px' } };
        const index = data.nodes.filter(x => x.id !== 'root').indexOf(n);
        const total = data.nodes.length - 1;
        return { ...n, type: 'card', position: { x: (index - (total - 1) / 2) * 380, y: 200 } };
      });
      const formattedEdges = data.edges.map(e => ({ ...e, type: 'smoothstep', animated: true, style: { stroke: '#b91c1c', strokeWidth: 1.5 } }));

      setNodes(formattedNodes);
      setEdges(formattedEdges);
      fetchHistory();
    } catch (err) {
      alert("Ошибка API! Убедитесь, что бэкенд запущен.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-screen h-screen bg-[#0d0d0d] text-white flex flex-col relative overflow-hidden font-sans">
      
      {/* Окно Истории */}
      <div className={`absolute top-0 right-0 h-full w-[300px] bg-[#111] border-l border-[#222] z-50 transform transition-transform duration-300 ${showHistory ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="p-4 flex justify-between items-center border-b border-[#222]">
          <h2 className="font-bold flex items-center gap-2"><History size={18} /> История</h2>
          <button onClick={() => setShowHistory(false)} className="text-gray-400 hover:text-white"><X size={20} /></button>
        </div>
        <div className="p-4 space-y-2 overflow-y-auto">
          {history.length === 0 ? <p className="text-gray-500 text-sm">История пуста</p> : 
            history.map((h, i) => (
              <div key={i} onClick={() => handleSearch(h.query)} className="bg-[#1a1a1a] p-3 rounded cursor-pointer hover:bg-[#222] transition flex justify-between">
                <span className="text-sm">{h.query}</span>
                <span className="text-xs text-gray-500">{h.time}</span>
              </div>
            ))
          }
        </div>
      </div>

      <div className="absolute inset-0 z-0">
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.2}>
          <Background color="#333333" gap={24} size={1} />
        </ReactFlow>
      </div>

      <div className="absolute top-10 left-0 right-0 z-10 flex flex-col items-center pointer-events-none px-4">
        
        {/* Кнопка истории */}
        <button onClick={() => setShowHistory(true)} className="absolute right-10 top-0 pointer-events-auto bg-[#161616] border border-[#333] p-3 rounded-full hover:bg-[#222] transition">
          <History size={20} />
        </button>

        <div className="text-4xl mb-4 text-white">⚡</div>
        <h1 className="text-4xl font-bold tracking-tight mb-2 uppercase">STARK OSINT</h1>
        <p className="text-[#888888] text-[14px] mb-6">Автоматический поиск по 900+ инструментам</p>

        <div className="w-full max-w-2xl relative pointer-events-auto">
          <input
            type="text"
            placeholder="ФИО, телефон, email, /passport, /inn, /adr..."
            className="w-full bg-[#161616] border border-[#333] rounded-full py-4 pl-6 pr-14 text-white focus:outline-none focus:border-[#555] transition shadow-2xl placeholder-[#555]"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={() => handleSearch()} disabled={loading} className="absolute right-2 top-2 bottom-2 bg-[#2563eb] hover:bg-blue-600 w-12 rounded-full flex items-center justify-center transition">
            {loading ? <span className="animate-spin text-sm">⏳</span> : <Send size={18} />}
          </button>
        </div>

        {/* Подсказки */}
        <div className="mt-4 flex flex-wrap justify-center gap-3 text-[11px] text-[#666] pointer-events-auto max-w-3xl">
            <span className="flex items-center gap-1"><HelpCircle size={12}/> Примеры:</span>
            <span className="bg-[#1a1a1a] px-2 py-1 rounded cursor-pointer hover:text-white transition" onClick={() => setQuery('79999688666')}>📱 Телефон</span>
            <span className="bg-[#1a1a1a] px-2 py-1 rounded cursor-pointer hover:text-white transition" onClick={() => setQuery('test@mail.ru')}>📧 Email</span>
            <span className="bg-[#1a1a1a] px-2 py-1 rounded cursor-pointer hover:text-white transition" onClick={() => setQuery('8.8.8.8')}>🌐 IP</span>
            <span className="bg-[#1a1a1a] px-2 py-1 rounded cursor-pointer hover:text-white transition" onClick={() => setQuery('durov')}>💬 Никнейм</span>
            <span className="bg-[#1a1a1a] px-2 py-1 rounded cursor-pointer hover:text-white transition" onClick={() => setQuery('google.com')}>🔗 Домен</span>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fadeIn 0.4s ease-out forwards; }
      `}</style>
    </div>
  );
}