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
import { AudioWaveform, Feather, Music, SlidersHorizontal, Sparkles } from 'lucide-react'
import type { Preset } from '../api'
import '@xyflow/react/dist/style.css'

type AgentData = { label: string; role: string; kind: string }

const icons = {
  conductor: AudioWaveform,
  lyrics: Feather,
  melody: Music,
  arrange: SlidersHorizontal,
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
  const includeLyrics = preset !== 'classical_instrumental'
  const definitions = [
    ['conductor', '指挥', '分析与分工'],
    ...(includeLyrics ? [['lyrics', '作词', '歌词与 Hook']] : []),
    ['melody', '作曲', '旋律与和声'],
    ['arrange', '编曲', '配器与织体'],
    ['prompt', '提示词', '汇总与编译'],
  ]
  const gap = 210
  const nodes: Node<AgentData>[] = definitions.map(([kind, label, role], index) => ({
    id: kind,
    type: 'agent',
    position: { x: 38 + index * gap, y: 92 },
    data: { kind, label, role },
  }))
  const edges = nodes.slice(1).map((node, index) => ({
    id: `${nodes[index].id}-${node.id}`,
    source: nodes[index].id,
    target: node.id,
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
