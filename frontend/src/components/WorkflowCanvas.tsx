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

function graphForPreset(preset: Preset): { nodes: Node<AgentData>[]; edges: Edge[] } {
  type EdgePair = [string, string, string?, string?]
  const definitions: Array<[string, string, string, number, number]> = [
    ['conductor', '指挥', '分析与分工', 20, 88],
    ...(preset === 'pop_vocal' || preset === 'auto'
      ? [['lyrics', '作词', '歌词与 Hook', 170, 38] as [string, string, string, number, number]]
      : []),
    ...(preset === 'electronic_instrumental'
      ? [['rhythm', '节奏', 'Groove 与低频', 170, 138] as [string, string, string, number, number]]
      : []),
    ['melody', '作曲', '主题与旋律', 320, 88],
    ['harmony', '和声', '张力与进行', 470, 38],
    ...(preset !== 'electronic_instrumental'
      ? [['rhythm', '节奏', '律动与能量', 470, 138] as [string, string, string, number, number]]
      : []),
    ['arrange', '编曲', '配器与织体', 620, 88],
    ['sound', '音色', '声景与质感', 770, 38],
    ['review', '审听', '平衡与风险', 770, 138],
    ['prompt', '提示词', '汇总与编译', 920, 88],
  ]
  const nodes: Node<AgentData>[] = definitions.map(([kind, label, role, x, y]) => ({
    id: kind,
    type: 'agent',
    position: { x, y },
    data: { kind, label, role },
  }))
  const edgePairs: EdgePair[] =
    preset === 'electronic_instrumental'
      ? [
          ['conductor', 'rhythm'] as EdgePair,
          ['rhythm', 'melody'] as EdgePair,
          ['melody', 'harmony'] as EdgePair,
          ['harmony', 'arrange', 'right-source', 'left-target'],
          ['arrange', 'sound'] as EdgePair,
          ['sound', 'review', 'bottom-source', 'top-target'],
          ['review', 'prompt'] as EdgePair,
        ]
      : [
          ['conductor', preset === 'classical_instrumental' || preset === 'soundtrack_score' ? 'melody' : 'lyrics'] as EdgePair,
          ...(preset === 'classical_instrumental' || preset === 'soundtrack_score' ? [] : [['lyrics', 'melody'] as EdgePair]),
          ['melody', 'harmony'] as EdgePair,
          ...(preset === 'classical_instrumental' || preset === 'soundtrack_score' ? [] : [['harmony', 'rhythm', 'bottom-source', 'top-target'] as EdgePair]),
          [preset === 'classical_instrumental' || preset === 'soundtrack_score' ? 'harmony' : 'rhythm', 'arrange', 'right-source', 'left-target'],
          ['arrange', 'sound'] as EdgePair,
          ['sound', 'review', 'bottom-source', 'top-target'],
          ['review', 'prompt'] as EdgePair,
        ]
  const edges = edgePairs.map(([source, target, sourceHandle = 'right-source', targetHandle = 'left-target']) => ({
    id: `${source}-${target}`,
    source,
    target,
    sourceHandle,
    targetHandle,
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
    style: { stroke: '#7b8a82', strokeWidth: 2 },
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
