import './Home.css';
import {
  IonPage,
  IonContent,
  IonSpinner,
} from '@ionic/react';
import React, { useEffect, useState }  from 'react';
import { useHistory } from 'react-router';
import SearchWithScan from '../../components/SearchWithScan/SearchWithScan';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { chatboxEllipsesOutline } from 'ionicons/icons';
import Analysis from './Analysis/Analysis';
import { API_BASE_URL } from '../../api/config';

const IMAGE_BASE_URL = `${API_BASE_URL}/processed_files`;



interface SimilarImage {
  doc_name: string;
  image_name: string;
  image_path: string;
  similarity_score: number;
}

const Home: React.FC = () => {
  const history = useHistory();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.user);
  const { chatId } = useAppSelector((state) => state.chat);
  
  const [searchResults, setSearchResults] = useState<{
    similarImages: Array<{filename: string; similarity: number}>;
    ragResponse: string;
  } | null>(null);
  const [similarImages, setSimilarImages] = useState<SimilarImage[]>([]);
  const [analysis, setAnalysis] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const handleSearchResults = async (results: { similar_images: SimilarImage[] }) => {
    setSimilarImages(results.similar_images);
    console.log(results);
    
    if (results.similar_images.length > 0) {
      setIsAnalyzing(true);
      try {
        const firstImage = results.similar_images[0];
        const ragQuery = await fetch(`${API_BASE_URL}/rag/graph/ask`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            text: `What is this image about: ${firstImage.image_name}?`
          }),
        });

        if (ragQuery.ok) {
          const result = await ragQuery.json();
          console.log(result);
          setAnalysis(result.answer);
        }
      } catch (error) {
        console.error('Error analyzing image:', error);
      } finally {
        setIsAnalyzing(false);
      }
    }
  };
  return (
    <IonPage>
      <Header title={`Hello, ${user?.name}`} noBorder />
      <IonContent>
        <Container padding={false}>
          <Analysis />
          <SearchWithScan
            placeholder="Search similar content or images"
            onSearchResults={handleSearchResults}
          />
          
          {analysis && (
            <div className="analysis-container">
              <h2>Relevant Analysis using image with highest similarity</h2>
              {isAnalyzing ? (
                <IonSpinner />
              ) : (
                <p>{analysis}</p>
              )}
            </div>
          )}

          {similarImages.length > 0 && (
            <div className="similar-images">
              <h2>Similar Images</h2>
              <div className="image-grid">
                {similarImages.map((img, index) => (
                  <div key={index} className="similar-image-item">
                    <img 
                      src={`${IMAGE_BASE_URL}/${img.doc_name}/${img.image_name}`} 
                      alt={`Similar ${index + 1}`} 
                    />
                    <p>Document: {img.doc_name}</p>
                    <p>Similarity: {(img.similarity_score * 100).toFixed(1)}%</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Container>
      </IonContent>
    </IonPage>
  );
};

export default Home;