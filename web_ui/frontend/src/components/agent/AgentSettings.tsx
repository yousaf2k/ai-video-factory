/**
 * Agent settings — LLM config, tool enable/disable toggles, MCP servers, skills.
 */
'use client';

import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  AlertTriangle, Bot, Check, Loader2, Plug, Plus, Sparkles, Trash2, Wrench, X,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { api, getApiErrorMessage } from '@/services/api';
import {
  useAgentConfig, useAgentSkillActions, useTestAgentLlm, useUpdateAgentConfig,
} from '@/hooks/useAgent';
import type { AgentToolInfo, McpServerConfig } from '@/types/agent';
import { cn } from '@/lib/utils';

/* --------------------------------------------------------------- General */

function GeneralSettings() {
  const { data, isLoading } = useAgentConfig();
  const update = useUpdateAgentConfig();
  const test = useTestAgentLlm();
  const [customModel, setCustomModel] = useState(false);

  if (isLoading || !data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const cfg = data.config;

  // The model list follows whichever provider will actually run.
  const effectiveProvider = cfg.provider || cfg.effective_provider || 'gemini';
  const models = cfg.provider_models?.[effectiveProvider] ?? [];
  const savedModelIsKnown = !cfg.model || models.includes(cfg.model);
  const showCustomInput = customModel || !!cfg.model && !savedModelIsKnown;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>LLM provider</Label>
          <Select
            value={cfg.provider || '__app__'}
            onValueChange={(v) => update.mutate({ provider: v === '__app__' ? '' : v })}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__app__">
                Follow app LLM (currently {cfg.effective_provider || '—'})
              </SelectItem>
              {data.llm_providers.map((p) => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Independent from the story-generation LLM. Keys/base URLs come from the
            main Configuration page.
          </p>
        </div>
        <div className="space-y-1.5">
          <Label>Model</Label>
          <Select
            value={showCustomInput ? '__custom__' : (cfg.model || '__default__')}
            onValueChange={(v) => {
              if (v === '__default__') {
                setCustomModel(false);
                update.mutate({ model: '' });
              } else if (v === '__custom__') {
                setCustomModel(true);
              } else {
                setCustomModel(false);
                update.mutate({ model: v });
              }
            }}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__default__">
                {effectiveProvider} default{cfg.effective_model ? ` (${cfg.effective_model})` : ''}
              </SelectItem>
              {models.map((m) => (
                <SelectItem key={m} value={m}>{m}</SelectItem>
              ))}
              <SelectItem value="__custom__">Custom…</SelectItem>
            </SelectContent>
          </Select>
          {showCustomInput && (
            <Input
              placeholder="custom model name, e.g. deepseek-chat"
              defaultValue={savedModelIsKnown ? '' : cfg.model}
              onBlur={(e) => {
                if (e.target.value.trim()) update.mutate({ model: e.target.value.trim() });
              }}
            />
          )}
          <p className="text-xs text-muted-foreground">
            Applies to the agent only; the story pipeline keeps its own model.
          </p>
        </div>
        <div className="space-y-1.5">
          <Label>Effort / thinking</Label>
          {cfg.effort_supported ? (
            <Select
              value={cfg.effort || '__auto__'}
              onValueChange={(v) => update.mutate({ effort: v === '__auto__' ? '' : v })}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__auto__">Auto — model default (nothing sent)</SelectItem>
                {cfg.effort_options.map((e) => (
                  <SelectItem key={e} value={e}>
                    {e.charAt(0).toUpperCase() + e.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input disabled placeholder="No effort setting for this provider/model" />
          )}
          <p className="text-xs text-muted-foreground">
            {cfg.effort_supported
              ? 'Higher effort = deeper reasoning (slower, more tokens). Auto sends no parameter and the model picks its own default.'
              : `${effectiveProvider} / ${cfg.effective_model || 'this model'} has no effort setting — it uses its built-in default.`}
          </p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="agent-iterations">Max tool iterations per message</Label>
          <Input
            id="agent-iterations"
            type="number"
            min={1}
            max={50}
            defaultValue={cfg.max_iterations}
            onBlur={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!Number.isNaN(v) && v !== cfg.max_iterations) update.mutate({ max_iterations: v });
            }}
          />
        </div>
        <div className="flex items-center gap-3 pt-6">
          <Switch
            id="agent-dangerous"
            checked={cfg.dangerous_tools_allowed}
            onCheckedChange={(v) => update.mutate({ dangerous_tools_allowed: v })}
          />
          <div>
            <Label htmlFor="agent-dangerous">Allow dangerous tools</Label>
            <p className="text-xs text-muted-foreground">delete_project, delete_shot, delete_file…</p>
          </div>
        </div>
        <div className="flex items-center gap-3 sm:col-span-2">
          <Switch
            id="agent-context"
            checked={cfg.auto_include_project_context}
            onCheckedChange={(v) => update.mutate({ auto_include_project_context: v })}
          />
          <div>
            <Label htmlFor="agent-context">Inject active project context</Label>
            <p className="text-xs text-muted-foreground">
              The agent automatically sees a summary of the project open in the UI.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="agent-extra">Extra system instructions</Label>
        <Textarea
          id="agent-extra"
          rows={4}
          placeholder="Custom persona or rules appended to the agent's system prompt…"
          defaultValue={cfg.extra_system_prompt}
          onBlur={(e) => {
            if (e.target.value !== cfg.extra_system_prompt) update.mutate({ extra_system_prompt: e.target.value });
          }}
        />
      </div>

      <div className="flex items-center gap-3">
        <Button
          size="sm"
          variant="outline"
          onClick={() => test.mutate()}
          disabled={test.isPending}
        >
          {test.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Test agent LLM
        </Button>
        {test.data && (
          <span
            className={cn(
              'text-sm',
              test.data.ok ? 'text-emerald-400' : 'text-red-500',
            )}
          >
            {test.data.ok
              ? `✓ ${test.data.provider} · ${test.data.model || 'default'} replied “${test.data.reply}”`
              : `✗ ${test.data.error}`}
          </span>
        )}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- Tools */

function ToolsSettings() {
  const { data, isLoading } = useAgentConfig();
  const update = useUpdateAgentConfig();
  const [search, setSearch] = useState('');

  const grouped = useMemo(() => {
    const groups = new Map<string, AgentToolInfo[]>();
    for (const t of data?.tools ?? []) {
      if (search && !`${t.name} ${t.description}`.toLowerCase().includes(search.toLowerCase())) continue;
      const list = groups.get(t.category) ?? [];
      list.push(t);
      groups.set(t.category, list);
    }
    return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [data, search]);

  if (isLoading || !data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const enabledCount = data.tools.filter((t) => t.enabled).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search tools…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <span className="text-xs text-muted-foreground">
          {enabledCount}/{data.tools.length} enabled
        </span>
        {!data.config.dangerous_tools_allowed && (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-1 text-[11px] text-amber-500">
            <AlertTriangle className="h-3 w-3" /> dangerous tools hidden — enable in General
          </span>
        )}
      </div>
      {grouped.map(([category, tools]) => (
        <div key={category} className="rounded-lg border">
          <div className="border-b bg-muted/40 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {category} ({tools.length})
          </div>
          <div className="divide-y">
            {tools.map((t) => (
              <div key={t.name} className="flex items-start gap-3 px-3 py-2">
                <Switch
                  checked={t.enabled}
                  disabled={t.blocked_by_dangerous_gate}
                  onCheckedChange={(v) => update.mutate({ enabled_tools: { [t.name]: v } })}
                  className="mt-0.5"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    {t.name}
                    {t.dangerous && (
                      <span className="ml-2 rounded bg-red-500/10 px-1.5 py-0.5 text-[10px] font-normal text-red-500">
                        dangerous
                      </span>
                    )}
                    {t.blocked_by_dangerous_gate && (
                      <span className="ml-2 text-[10px] text-muted-foreground">(blocked)</span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground">{t.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------- MCP */

function McpSettings() {
  const { data, isLoading } = useAgentConfig();
  const update = useUpdateAgentConfig();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [probing, setProbing] = useState<string | null>(null);
  const [probeResults, setProbeResults] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    name: '', transport: 'stdio' as 'stdio' | 'http',
    command: '', args: '', url: '',
  });

  if (isLoading || !data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const servers = data.config.mcp_servers ?? {};

  const addServer = () => {
    if (!form.name.trim()) {
      toast.error('Server name is required');
      return;
    }
    if (servers[form.name]) {
      toast.error('A server with that name already exists');
      return;
    }
    const server: McpServerConfig = {
      transport: form.transport,
      enabled: true,
      ...(form.transport === 'stdio'
        ? {
            command: form.command,
            args: form.args.split(/\s+/).filter(Boolean),
          }
        : { url: form.url }),
    };
    update.mutate(
      { mcp_servers: { ...servers, [form.name]: server } },
      {
        onSuccess: () => {
          toast.success(`MCP server "${form.name}" added`);
          setDialogOpen(false);
          setForm({ name: '', transport: 'stdio', command: '', args: '', url: '' });
        },
      },
    );
  };

  const setServer = (name: string, patch: Partial<McpServerConfig>) =>
    update.mutate({ mcp_servers: { ...servers, [name]: { ...servers[name], ...patch } } });

  const removeServer = (name: string) => {
    const next = { ...servers };
    delete next[name];
    update.mutate({ mcp_servers: next });
  };

  const probe = async (name: string) => {
    setProbing(name);
    try {
      const result = await api.listMcpServerTools(name);
      setProbeResults((p) => ({
        ...p,
        [name]: `✓ connected — ${result.tools.length} tools: ${result.tools.slice(0, 6).map((t) => t.name).join(', ')}${result.tools.length > 6 ? '…' : ''}`,
      }));
    } catch (error) {
      setProbeResults((p) => ({ ...p, [name]: `✗ ${getApiErrorMessage(error, 'connection failed')}` }));
    } finally {
      setProbing(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          External MCP servers give the agent extra tools (named <code>mcp__server__tool</code>).
        </p>
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="mr-1.5 h-4 w-4" /> Add server
        </Button>
      </div>

      {Object.keys(servers).length === 0 && (
        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          <Plug className="mx-auto mb-2 h-6 w-6 opacity-40" />
          No MCP servers configured. Add one via stdio (e.g.&nbsp;
          <code>npx -y @modelcontextprotocol/server-filesystem</code>) or HTTP.
        </div>
      )}

      {Object.entries(servers).map(([name, server]) => (
        <div key={name} className="rounded-lg border p-3">
          <div className="flex flex-wrap items-center gap-3">
            <Switch checked={server.enabled} onCheckedChange={(v) => setServer(name, { enabled: v })} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {server.transport === 'stdio'
                  ? `$ ${server.command} ${(server.args ?? []).join(' ')}`
                  : server.url}
              </p>
            </div>
            <Button size="sm" variant="outline" disabled={probing === name} onClick={() => probe(name)}>
              {probing === name && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
              Test
            </Button>
            <Button size="sm" variant="ghost" onClick={() => removeServer(name)} title="Remove">
              <Trash2 className="h-4 w-4 text-red-500" />
            </Button>
          </div>
          {probeResults[name] && (
            <p
              className={cn(
                'mt-2 break-all rounded bg-muted/50 px-2 py-1 text-xs',
                probeResults[name].startsWith('✓')
                  ? 'text-emerald-400'
                  : 'text-red-500',
              )}
            >
              {probeResults[name]}
            </p>
          )}
        </div>
      ))}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add MCP server</DialogTitle>
            <DialogDescription>
              stdio: a local command (npx/uvx/python). http: a streamable-HTTP MCP endpoint.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="filesystem"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Transport</Label>
              <Select
                value={form.transport}
                onValueChange={(v) => setForm((f) => ({ ...f, transport: v as 'stdio' | 'http' }))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="stdio">stdio (command)</SelectItem>
                  <SelectItem value="http">http (URL)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.transport === 'stdio' ? (
              <>
                <div className="space-y-1.5">
                  <Label>Command</Label>
                  <Input
                    value={form.command}
                    onChange={(e) => setForm((f) => ({ ...f, command: e.target.value }))}
                    placeholder="npx"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Arguments (space-separated)</Label>
                  <Input
                    value={form.args}
                    onChange={(e) => setForm((f) => ({ ...f, args: e.target.value }))}
                    placeholder="-y @modelcontextprotocol/server-filesystem C:/some/dir"
                  />
                </div>
              </>
            ) : (
              <div className="space-y-1.5">
                <Label>URL</Label>
                <Input
                  value={form.url}
                  onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
                  placeholder="http://localhost:3333/mcp"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button size="sm" onClick={addServer}>Add</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* --------------------------------------------------------------- Skills */

function SkillsSettings() {
  const { data, isLoading } = useAgentConfig();
  const { create, remove } = useAgentSkillActions();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', content: '' });

  if (isLoading || !data) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Reusable playbooks the agent loads on demand. Files live in{' '}
          <code>agent_skills/&lt;name&gt;/SKILL.md</code>.
        </p>
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="mr-1.5 h-4 w-4" /> New skill
        </Button>
      </div>

      {data.skills.length === 0 && (
        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          <Sparkles className="mx-auto mb-2 h-6 w-6 opacity-40" />
          No skills yet — create one to teach the agent a repeatable workflow.
        </div>
      )}

      {data.skills.map((skill) => (
        <div key={skill.name} className="flex items-start gap-3 rounded-lg border p-3">
          <Sparkles className="mt-0.5 h-4 w-4 text-primary" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">{skill.name}</p>
            <p className="text-xs text-muted-foreground">{skill.description || '(no description)'}</p>
          </div>
          <Button
            size="sm" variant="ghost" title="Delete skill"
            onClick={() => remove.mutate(skill.name)}
          >
            <Trash2 className="h-4 w-4 text-red-500" />
          </Button>
        </div>
      ))}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>New skill</DialogTitle>
            <DialogDescription>
              Write the description as a trigger condition — when the agent should use it.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Name (folder)</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="batch-restyle-shots"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Input
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Use when the user wants all shots restyled to a new visual style"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Instructions (markdown)</Label>
              <Textarea
                rows={8}
                value={form.content}
                onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                placeholder={'1. list_shots\n2. update_shot for each with new image_prompt…'}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              size="sm"
              disabled={create.isPending}
              onClick={() =>
                create.mutate(form, {
                  onSuccess: () => {
                    setDialogOpen(false);
                    setForm({ name: '', description: '', content: '' });
                  },
                })
              }
            >
              {create.isPending && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ------------------------------------------------------------- container */

export function AgentSettings() {
  return (
    <Tabs defaultValue="general" className="w-full">
      <TabsList className="grid w-full grid-cols-4">
        <TabsTrigger value="general"><Bot className="mr-1.5 h-4 w-4" />General</TabsTrigger>
        <TabsTrigger value="tools"><Wrench className="mr-1.5 h-4 w-4" />Tools</TabsTrigger>
        <TabsTrigger value="mcp"><Plug className="mr-1.5 h-4 w-4" />MCP</TabsTrigger>
        <TabsTrigger value="skills"><Sparkles className="mr-1.5 h-4 w-4" />Skills</TabsTrigger>
      </TabsList>
      <TabsContent value="general" className="mt-4"><GeneralSettings /></TabsContent>
      <TabsContent value="tools" className="mt-4"><ToolsSettings /></TabsContent>
      <TabsContent value="mcp" className="mt-4"><McpSettings /></TabsContent>
      <TabsContent value="skills" className="mt-4"><SkillsSettings /></TabsContent>
    </Tabs>
  );
}
