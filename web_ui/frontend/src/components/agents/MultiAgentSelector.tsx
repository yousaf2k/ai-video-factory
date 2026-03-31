"use client";

import * as React from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "lucide-react"; // Using lucide for icons
import { Input } from "@/components/ui/input";
import { Search, X, Layers, Brain, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface Agent {
  id: string;
  name: string;
  type: string;
}

interface MultiAgentSelectorProps {
  availableAgents: Agent[];
  selectedValue: string;
  onChange: (value: string) => void;
  label?: string;
}

export function MultiAgentSelector({
  availableAgents,
  selectedValue,
  onChange,
  label
}: MultiAgentSelectorProps) {
  const [search, setSearch] = React.useState("");
  
  // Parse currently selected agents
  const selectedIds = React.useMemo(() => 
    selectedValue ? selectedValue.split(",").map(s => s.trim()) : [], 
    [selectedValue]
  );

  const toggleAgent = (id: string) => {
    let newSelected;
    if (selectedIds.includes(id)) {
      newSelected = selectedIds.filter(i => i !== id);
    } else {
      newSelected = [...selectedIds, id];
    }
    onChange(newSelected.join(","));
  };

  const filteredAgents = availableAgents.filter(a => 
    a.name.toLowerCase().includes(search.toLowerCase()) || 
    a.id.toLowerCase().includes(search.toLowerCase())
  );

  // Group agents for better UI
  const categories = React.useMemo(() => {
    const cats: Record<string, Agent[]> = {
      "Base / Schema": [],
      "Style / Narrative": [],
      "Context / Topic": [],
      "Other": []
    };

    filteredAgents.forEach(agent => {
      const id = agent.id.toLowerCase();
      if (id.includes("base_")) cats["Base / Schema"].push(agent);
      else if (id.includes("style_")) cats["Style / Narrative"].push(agent);
      else if (id.includes("context_")) cats["Context / Topic"].push(agent);
      else cats["Other"].push(agent);
    });

    return cats;
  }, [filteredAgents]);

  return (
    <div className="space-y-3">
      {label && <Label className="text-sm font-semibold text-muted-foreground">{label}</Label>}
      
      {/* Search and Selection Summary */}
      <div className="flex flex-col gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-muted/30 border-border/50 focus-visible:ring-primary/30"
          />
        </div>
        
        {selectedIds.length > 0 && (
          <div className="flex flex-wrap gap-1.5 p-2 bg-muted/20 rounded-md border border-dashed border-border/50 min-h-[40px] items-center">
             {selectedIds.map(id => {
               const agent = availableAgents.find(a => a.id === id);
               return (
                 <div key={id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs font-semibold border border-primary/20">
                   {agent?.name || id}
                   <X 
                    className="w-3 h-3 cursor-pointer hover:text-primary-foreground hover:bg-primary rounded-full" 
                    onClick={() => toggleAgent(id)}
                   />
                 </div>
               );
             })}
          </div>
        )}
      </div>

      <div className="border rounded-xl bg-card shadow-inner-sm overflow-hidden">
        <ScrollArea className="h-[280px] px-4 py-2">
          {Object.entries(categories).map(([cat, agents]) => (
            agents.length > 0 && (
              <div key={cat} className="mb-4 last:mb-0">
                <div className="flex items-center gap-2 mb-2 sticky top-0 bg-card py-1 z-10">
                   {cat === "Base / Schema" && <FileText className="w-3.5 h-3.5 text-blue-500" />}
                   {cat === "Style / Narrative" && <Layers className="w-3.5 h-3.5 text-purple-500" />}
                   {cat === "Context / Topic" && <Brain className="w-3.5 h-3.5 text-amber-500" />}
                   <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">{cat}</h4>
                </div>
                <div className="grid grid-cols-1 gap-1">
                  {agents.map((agent) => (
                    <div 
                      key={agent.id} 
                      className={cn(
                        "flex items-center space-x-3 p-2 rounded-lg cursor-pointer transition-all hover:bg-muted/50 group border border-transparent",
                        selectedIds.includes(agent.id) && "bg-primary/5 border-primary/10"
                      )}
                      onClick={() => toggleAgent(agent.id)}
                    >
                      <Checkbox 
                        id={agent.id} 
                        checked={selectedIds.includes(agent.id)}
                        className="data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                      />
                      <div className="grid gap-0.5 leading-none">
                        <label
                          htmlFor={agent.id}
                          className="text-sm font-medium leading-none cursor-pointer group-hover:text-primary transition-colors"
                        >
                          {agent.name}
                        </label>
                        <p className="text-[10px] text-muted-foreground font-mono truncate max-w-[200px]">
                          {agent.id}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          ))}
          
          {filteredAgents.length === 0 && (
            <div className="py-8 text-center text-xs text-muted-foreground italic">
              No agents found matching "{search}"
            </div>
          )}
        </ScrollArea>
      </div>
      
      <p className="text-[10px] text-muted-foreground italic px-1">
        Pro tip: Select a **Base** for rules, a **Style** for narrative flow, and a **Context** for topic knowledge.
      </p>
    </div>
  );
}
