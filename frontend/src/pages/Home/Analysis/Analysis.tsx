import { IonCard, IonIcon, IonSkeletonText } from '@ionic/react';
import React, { useEffect, useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import 'swiper/swiper-bundle.min.css';
import './Analysis.css';
import {
  bookOutline,
  fileTrayOutline,
  flashOutline,
  todayOutline,
  trophyOutline,
  appsOutline,
  gitMergeOutline,
  libraryOutline,
  gitNetworkOutline,
} from 'ionicons/icons';
import { useAppSelector } from '../../../app/hooks';
import { get } from '../../../services/storage';
import { API_BASE_URL } from '../../../api/config';

// Add interface for graph stats
interface GraphStats {
  totalNodes: number;
  totalRelationships: number;
  totalDocuments: number;
  averageRelationsPerNode: number;
  lastIndexed: string;
}

// Slide options
const slideOpts = {
  spaceBetween: -10,
  slidesPerView: 1.2,
  pagination: { clickable: true },
  navigation: false,
  breakpoints: {
    640: {
      slidesPerView: 1.2,
    },
    768: {
      slidesPerView: 2,
    },
    1024: {
      slidesPerView: 2.8,
    },
  },
};

export default function Analysis() {
  const { user } = useAppSelector((state) => state.user);
  const [loading, setLoading] = useState(true);
  const [graphStats, setGraphStats] = useState<GraphStats>({
    totalNodes: 0,
    totalRelationships: 0,
    totalDocuments: 0,
    averageRelationsPerNode: 0,
    lastIndexed: '',
  });

  const fetchGraphStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/rag/graph/stats`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await get("token")}`
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch graph statistics');
      }
      const data = await response.json();
      setGraphStats(data);
    } catch (error) {
      console.error('Error fetching graph stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphStats();
  }, []);

  const cardOptions = [
    {
      title: 'Total Nodes',
      description: 'Total number of knowledge nodes in the graph',
      icon: appsOutline,
      value: graphStats.totalNodes,
    },
    {
      title: 'Total Relationships',
      description: 'Total connections between knowledge nodes',
      icon: gitMergeOutline,
      value: graphStats.totalRelationships,
    },
    // {
    //   title: 'Total Documents',
    //   description: 'Number of documents processed',
    //   icon: libraryOutline,
    //   value: graphStats.totalDocuments,
    // },
    {
      title: 'Avg. Relations per Node',
      description: 'Average connections per knowledge node',
      icon: gitNetworkOutline,
      value: graphStats.averageRelationsPerNode,
    },
  ];

  return (
    <div className="analysis-container">
      <Swiper {...slideOpts}>
        {cardOptions.map((item, index) => (
          <SwiperSlide key={index.toString()}>
            <IonCard
              className="analysis-card"
              color="dark"
              style={{
                backgroundColor: index % 2 === 0 ? '#f8f8f8 ' : '#f8f8f8',
                color: index % 2 === 0 ? '#666' : '#666',
                border: index % 2 === 0 ? 'none' : 'none',
              }}
            >
              <div
                className="card-icon"
                style={{
                  backgroundColor:
                    index % 2 === 0
                      ? 'var(--ion-color-primary)'
                      : 'var(--ion-color-secondary)',
                }}
              >
                <IonIcon
                  style={{
                    color: '#fff',
                  }}
                  icon={item.icon || fileTrayOutline}
                  size="small"
                />
              </div>
              <h4>{item.title}</h4>
              {loading ? (
                <div style={{ padding: '0 10px' }}>
                  <IonSkeletonText
                    animated
                    style={{
                      width: '60%',
                      height: '24px',
                      margin: '10px 0',
                      '--background-rgb': '200, 200, 200',
                    }}
                  />
                </div>
              ) : (
                <h1
                  style={{
                    color: '#666',
                  }}
                >
                  {item.title === 'Avg. Relations per Node'
                    ? graphStats.averageRelationsPerNode.toString()
                    : item.value.toString()}
                </h1>
              )}
              <p
                style={{
                  fontSize: '12px',
                  color: '#999',
                  margin: '8px 0',
                  paddingBottom: '8px',
                }}
              >
                {item.description}
              </p>
            </IonCard>
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}