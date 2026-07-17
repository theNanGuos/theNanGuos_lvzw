import { useMemo } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import { AudioWaveform, Drum, Feather, Music, Radio, SlidersHorizontal, Sparkles, Users, Wand2 } from 'lucide-react'
import type { Preset } from '../api'
import '@xyflow/react/dist/style.css'

type AgentStatus = 'queued' | 'running' | 'completed' | 'failed'
type AgentData = { label: string; role: string; kind: string; status: AgentStatus }

const icons = {
  conductor: AudioWaveform,
  lyrics: Feather,
  melody: Music,
  harmony: Wand2,
  rhythm: Drum,
  improvisation: Sparkles,
  performance: Users,
  arrange: SlidersHorizontal,
  sound: Radio,
  review: AudioWaveform,
  prompt: Sparkles,
}

function AgentNode({ data }: NodeProps<Node<AgentData>>) {
  const Icon = icons[data.kind as keyof typeof icons]
  return (
    <div className={`agent-node ${data.kind} ${data.status}`}>
      <Handle id="left-target" type="target" position={Position.Left} />
      <Handle id="top-target" type="target" position={Position.Top} />
      <span><Icon size={16} /></span>
      <div><strong>{data.label}</strong><small>{data.role}</small></div>
      <Handle id="right-source" type="source" position={Position.Right} />
      <Handle id="bottom-source" type="source" position={Position.Bottom} />
    </div>
  )
}

const nodeTypes = { agent: AgentNode }

function graphForPreset(
  preset: Preset,
  runStatus: 'idle' | 'running' | 'completed' | 'failed',
  currentStage: string,
): { nodes: Node<AgentData>[]; edges: Edge[] } {
  const agents: Record<string, [string, string]> = {
    conductor: ['指挥南郭', '分析与分工'],
    lyrics: ['作词南郭', '歌词与 Hook'],
    melody: ['旋律南郭', '主题与旋律'],
    harmony: ['和声南郭', '张力与进行'],
    rhythm: ['节奏南郭', 'Groove 与能量'],
    improvisation: ['即兴南郭', 'Solo 与乐手对话'],
    performance: ['演奏南郭', '动态与人性化'],
    arrange: ['编曲南郭', '配器与织体'],
    sound: ['音色南郭', '声景与质感'],
    review: ['审听南郭', '平衡与风险'],
    prompt: ['提示词南郭', '汇总与编译'],
  }
  const pipelines: Record<Preset, string[]> = {
    auto: ['conductor', 'lyrics', 'melody', 'harmony', 'rhythm', 'arrange', 'sound', 'review', 'prompt'],
    pop_vocal: ['conductor', 'lyrics', 'melody', 'harmony', 'rhythm', 'arrange', 'sound', 'review', 'prompt'],
    classical_instrumental: ['conductor', 'melody', 'harmony', 'arrange', 'sound', 'review', 'prompt'],
    electronic_instrumental: ['conductor', 'rhythm', 'melody', 'harmony', 'arrange', 'sound', 'review', 'prompt'],
    soundtrack_score: ['conductor', 'melody', 'harmony', 'arrange', 'sound', 'review', 'prompt'],
    jazz_ensemble: ['conductor', 'harmony', 'rhythm', 'melody', 'improvisation', 'performance', 'arrange', 'sound', 'review', 'prompt'],
    rock_vocal: ['conductor', 'lyrics', 'melody', 'harmony', 'rhythm', 'performance', 'arrange', 'sound', 'review', 'prompt'],
    folk_acoustic: ['conductor', 'lyrics', 'melody', 'harmony', 'performance', 'arrange', 'sound', 'review', 'prompt'],
    hiphop_vocal: ['conductor', 'rhythm', 'lyrics', 'melody', 'harmony', 'performance', 'arrange', 'sound', 'review', 'prompt'],
  }
  const pipeline = pipelines[preset]
  const definitions: Array<[string, string, string, number, number]> = pipeline.map((kind, index) => [
    kind,
    agents[kind][0],
    agents[kind][1],
    20 + index * 132,
    index % 2 === 0 ? 58 : 128,
  ])
  const workflowFinished = ['demo_audio', 'music_generation', 'audio_analysis', 'completed'].includes(currentStage)
  const nodes: Node<AgentData>[] = definitions.map(([kind, label, role, x, y], index) => ({
    id: kind,
    type: 'agent',
    position: { x, y },
    data: {
      kind,
      label,
      role,
      status: runStatus === 'completed' || workflowFinished
        ? 'completed'
        : runStatus === 'failed' && index === 0
          ? 'failed'
          : runStatus === 'running' && currentStage === 'workflow' && index === 0
            ? 'running'
            : 'queued',
    },
  }))
  const edges = pipeline.slice(0, -1).map((source, index) => ({
    id: `${source}-${pipeline[index + 1]}`,
    source,
    target: pipeline[index + 1],
    sourceHandle: 'right-source',
    targetHandle: 'left-target',
    markerEnd: { type: MarkerType.ArrowClosed, width: 20, height: 20, color: '#3f574c' },
    style: { stroke: '#3f574c', strokeWidth: 2.8 },
  }))
  return { nodes, edges }
}

export function WorkflowCanvas({
  preset,
  compact = false,
  runStatus = 'idle',
  currentStage = 'draft',
}: {
  preset: Preset
  compact?: boolean
  runStatus?: 'idle' | 'running' | 'completed' | 'failed'
  currentStage?: string
}) {
  const graph = useMemo(
    () => graphForPreset(preset, runStatus, currentStage),
    [currentStage, preset, runStatus],
  )
  return (
    <ReactFlow
      key={preset}
      className="workflow-flow"
      nodes={graph.nodes}
      edges={graph.edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: compact ? 0.2 : 0.25 }}
      minZoom={compact ? 0.2 : 0.35}
      maxZoom={1.5}
      nodesConnectable={false}
      elementsSelectable={!compact}
      panOnDrag={!compact}
      zoomOnScroll={!compact}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="#d9ddda" />
      {!compact && <Controls showInteractive={false} />}
    </ReactFlow>
  )
}
