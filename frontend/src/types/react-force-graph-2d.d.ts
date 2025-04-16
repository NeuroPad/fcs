declare module 'react-force-graph-2d' {
  import { Component } from 'react';

  export interface NodeObject {
    id: string | number;
    name?: string;
    val?: number;
    color?: string;
    x?: number;
    y?: number;
    [key: string]: any;
  }

  export interface LinkObject {
    id?: string | number;
    source: string | number | NodeObject;
    target: string | number | NodeObject;
    label?: string;
    color?: string;
    [key: string]: any;
  }

  export interface GraphData {
    nodes: NodeObject[];
    links: LinkObject[];
  }

  export interface ForceGraphMethods {
    centerAt: (x?: number, y?: number, milliseconds?: number) => void;
    zoom: (zoomLevel: number, milliseconds?: number) => void;
    zoomToFit: (milliseconds?: number, padding?: number) => void;
    pauseAnimation: () => void;
    resumeAnimation: () => void;
    d3Force: (forceName: string, forceInstance?: any) => any;
    d3ReheatSimulation: () => void;
  }

  export interface ForceGraph2DProps {
    graphData: GraphData;
    nodeRelSize?: number;
    // Fix the callback return types to allow undefined
    nodeVal?: (node: NodeObject) => number | undefined;
    nodeLabel?: (node: NodeObject) => string | undefined;
    nodeColor?: (node: NodeObject) => string | undefined;
    linkLabel?: (link: LinkObject) => string | undefined;
    linkWidth?: (link: LinkObject) => number | undefined;
    linkDirectionalArrowLength?: number;
    linkDirectionalArrowRelPos?: number;
    linkCurvature?: number;
    linkDirectionalParticles?: number;
    linkDirectionalParticleWidth?: (link: LinkObject) => number | undefined;
    onNodeHover?: (node: NodeObject | null, prevNode: NodeObject | null) => void;
    onLinkHover?: (link: LinkObject | null, prevLink: LinkObject | null) => void;
    cooldownTicks?: number;
    onEngineStop?: () => void;
    linkCanvasObjectMode?: () => string;
    linkCanvasObject?: (link: LinkObject, ctx: CanvasRenderingContext2D, globalScale?: number) => void;
    ref?: React.RefObject<ForceGraphMethods>;
    draggable?: boolean;
    [key: string]: any;
  }

  export default class ForceGraph2D extends Component<ForceGraph2DProps> implements ForceGraphMethods {
    centerAt(x?: number, y?: number, milliseconds?: number): void;
    zoom(zoomLevel: number, milliseconds?: number): void;
    zoomToFit(milliseconds?: number, padding?: number): void;
    pauseAnimation(): void;
    resumeAnimation(): void;
    d3Force(forceName: string, forceInstance?: any): any;
    d3ReheatSimulation(): void;
  }
}