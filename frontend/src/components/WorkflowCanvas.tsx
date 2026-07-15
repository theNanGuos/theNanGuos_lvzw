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
import { AudioWaveform, Drum, Feather, Music, Radio, SlidersHorizontal, Sparkles, Wand2 } from 'lucide-react'
import type { Preset } from '../api'
import '@xyflow/react/dist/style.css'

type AgentData = { label: string; role: string; kind: string }

const icons = {
  conductor: AudioWaveform,
  lyrics: Feather,
  melody: Music,
  harmony: Wand2,
  rhythm: Drum,
  arrange: SlidersHorizontal,
  sound: Radio,
  review: AudioWaveform,
  prompt: Sparkles,
}

function AgentNode({ data }: NodeProps<Node<AgentData>>) {
  const Icon = icons[data.kind as keyof typeof icons]
  return (
    <div className={`agent-node ${data.kind}`}>
      <Handle type="target" position={Position.Left} />
      <span><Icon size={16} /></span>
      <div><strong>{data.label}</strong><small>{data.role}</small></div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

const nodeTypes = { agent: AgentNode }

function graphForPreset(preset: Preset): { nodes: Node<AgentData>[]; edges: Edge[] } {
  const definitions: Array<[string, string, string, number, number]> = [
    ['conductor', '指挥', '分析与分工', 30, 88],
    ...(preset === 'pop_vocal' || preset === 'auto'
      ? [['lyrics', '作词', '歌词与 Hook', 225, 38] as [string, string, string, number, number]]
      : []),
    ...(preset === 'electronic_instrumental'
      ? [['rhythm', '节奏', 'Groove 与低频', 225, 138] as [string, string, string, number, number]]
      : []),
    ['melody', '作曲', '主题与旋律', 420, 88],
    ['harmony', '和声', '张力与进行', 615, 38],
    ...(preset !== 'electronic_instrumental'
      ? [['rhythm', '节奏', '律动与能量', 615, 138] as [string, string, string, number, number]]
      : []),
    ['arrange', '编曲', '配器与织体', 810, 88],
    ['sound', '音色', '声景与质感', 1005, 38],
    ['review', '审听', '平衡与风险', 1005, 138],
    ['prompt', '提示词', '汇总与编译', 1200, 88],
  ]
  const nodes: Node<AgentData>[] = definitions.map(([kind, label, role, x, y]) => ({
    id: kind,
    type: 'agent',
    position: { x, y },
    data: { kind, label, role },
  }))
  const edgePairs =
    preset === 'electronic_instrumental'
      ? [
          ['conductor', 'rhythm'],
          ['rhythm', 'melody'],
          ['melody', 'harmony'],
          ['harmony', 'arrange'],
          ['arrange', 'sound'],
          ['sound', 'review'],
          ['review', 'prompt'],
        ]
      : [
          ['conductor', preset === 'classical_instrumental' || preset === 'soundtrack_score' ? 'melody' : 'lyrics'],
          ...(preset === 'classical_instrumental' || preset === 'soundtrack_score' ? [] : [['lyrics', 'melody']]),
          ['melody', 'harmony'],
          ...(preset === 'classical_instrumental' || preset === 'soundtrack_score' ? [] : [['harmony', 'rhythm']]),
          [preset === 'classical_instrumental' || preset === 'soundtrack_score' ? 'harmony' : 'rhythm', 'arrange'],
          ['arrange', 'sound'],
          ['sound', 'review'],
          ['review', 'prompt'],
        ]
  const edges = edgePairs.map(([source, target]) => ({
    id: `${source}-${target}`,
    source,
    target,
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
    style: { stroke: '#85908b', strokeWidth: 1.5 },
  }))
  return { nodes, edges }
}

export function WorkflowCanvas({ preset, compact = false }: { preset: Preset; compact?: boolean }) {
  const graph = useMemo(() => graphForPreset(preset), [preset])
  return (
    <ReactFlow
      key={preset}
      nodes={graph.nodes}
      edges={graph.edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: compact ? 0.12 : 0.25 }}
      minZoom={0.45}
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
