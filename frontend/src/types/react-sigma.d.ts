declare module 'react-sigma' {
  import { Component, ReactNode } from 'react';

  export interface NodeObject {
    id: string;
    label?: string;
    x?: number;
    y?: number;
    size?: number;
    color?: string;
    [key: string]: any;
  }

  export interface EdgeObject {
    id: string;
    source: string;
    target: string;
    label?: string;
    color?: string;
    size?: number;
    type?: string;
    [key: string]: any;
  }

  export interface GraphData {
    nodes: NodeObject[];
    edges: EdgeObject[];
  }

  export interface SigmaProps {
    graph?: GraphData;
    settings?: any;
    style?: React.CSSProperties;
    renderer?: 'canvas' | 'webgl' | 'svg';
    onClickNode?: (e: any) => void;
    onOverNode?: (e: any) => void;
    onOutNode?: (e: any) => void;
    onClickEdge?: (e: any) => void;
    onOverEdge?: (e: any) => void;
    onOutEdge?: (e: any) => void;
    onSigmaInstanceCreated?: (sigma: any) => void;
    children?: ReactNode;
  }

  export class Sigma extends Component<SigmaProps> {}
  
  export interface LoadJSONProps {
    path: string;
    children?: ReactNode;
  }
  
  export class LoadJSON extends Component<LoadJSONProps> {}
  
  export interface RandomizeNodePositionsProps {
    children?: ReactNode;
  }
  
  export class RandomizeNodePositions extends Component<RandomizeNodePositionsProps> {}
  
  export interface RelativeSizeProps {
    initialSize?: number;
    children?: ReactNode;
  }
  
  export class RelativeSize extends Component<RelativeSizeProps> {}
  
  export interface FilterProps {
    neighborsOf?: string;
    children?: ReactNode;
  }
  
  export class Filter extends Component<FilterProps> {}
  
  export interface ForceAtlas2Props {
    worker?: boolean;
    barnesHutOptimize?: boolean;
    barnesHutTheta?: number;
    iterationsPerRender?: number;
    linLogMode?: boolean;
    timeout?: number;
    gravity?: number;
    scalingRatio?: number;
    strongGravityMode?: boolean;
    slowDown?: number;
    children?: ReactNode;
  }
  
  export class ForceAtlas2 extends Component<ForceAtlas2Props> {}
  
  export class SigmaEnableWebGL extends Component {}
  
  export class SigmaEnableSVG extends Component {}
  
  export interface EdgeShapesProps {
    default: string;
    children?: ReactNode;
  }
  
  export class EdgeShapes extends Component<EdgeShapesProps> {}
  
  export interface NodeShapesProps {
    default: string;
    children?: ReactNode;
  }
  
  export class NodeShapes extends Component<NodeShapesProps> {}
  
  export interface LoadGEXFProps {
    path: string;
    children?: ReactNode;
  }
  
  export class LoadGEXF extends Component<LoadGEXFProps> {}
}