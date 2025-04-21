import React, { useState, useRef } from 'react';
import { IonIcon, IonButton, IonSearchbar, IonContent, IonModal } from '@ionic/react';
import { scanOutline } from 'ionicons/icons';
import { Camera, CameraResultType } from '@capacitor/camera';
import Cropper, { ReactCropperElement } from 'react-cropper';
import { API_BASE_URL } from '../../api/config';
import 'cropperjs/dist/cropper.css';
import './SearchWithScan.css';

interface SimilarImage {
  doc_name: string;
  image_name: string;
  image_path: string;
  similarity_score: number;
}

interface SearchWithScanProps {
  placeholder?: string;
  onSearchResults?: (results: { similar_images: SimilarImage[] }) => void;
}

const SearchWithScan: React.FC<SearchWithScanProps> = ({
  placeholder = 'Search or scan an image',
  onSearchResults,
}) => {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [showCropper, setShowCropper] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const cropperRef = useRef<ReactCropperElement>(null);
  const [searchText, setSearchText] = useState('');

  const handleScanClick = async () => {
    try {
      const photo = await Camera.getPhoto({
        quality: 90,
        allowEditing: false,
        resultType: CameraResultType.DataUrl,
      });

      if (photo?.dataUrl) {
        setImageSrc(photo.dataUrl);
        setShowCropper(true);
      }
    } catch (error) {
      console.error('Error capturing image:', error);
    }
  };

  const processImage = async () => {
    const cropper = cropperRef.current?.cropper;
    if (cropper) {
      cropper.getCroppedCanvas().toBlob(async (blob) => {
        if (blob) {
          setIsLoading(true);
          const formData = new FormData();
          formData.append('file', blob, 'image.png');
          formData.append('top_k', '5');

          try {
            const response = await fetch(`${API_BASE_URL}/graph-rag/find-similar`, {
              method: 'POST',
              body: formData,
            });

            if (response.ok) {
              const data = await response.json();
              onSearchResults?.(data);
              setShowCropper(false);
              setImageSrc(null);
            }
          } catch (error) {
            console.error('Error processing image:', error);
          } finally {
            setIsLoading(false);
          }
        }
      }, 'image/png');
    }
  };

  return (
    <div className="search-with-scan-container">
      <div className="search-bar-container">
        {/* <IonSearchbar
          value={searchText}
          onIonInput={(e) => {
            const value = e.detail.value || '';
            setSearchText(value);
          }}
          placeholder={placeholder}
          className="custom-searchbar"
        /> */}
        {/* <IonButton
          expand="block"
          fill="solid"
          color="primary"
          className="ion-margin-horizontal"
          onClick={handleScanClick}
        >
          <IonIcon style={{ color: "#fff" }} icon={scanOutline} slot="start" />
          Search an image and analyze
        </IonButton> */}
        {/* <div className="scan-button" onClick={handleScanClick}>
          <IonIcon icon={scanOutline} />
        </div> */}
      </div>

      <IonModal isOpen={showCropper} onDidDismiss={() => setShowCropper(false)}>
        <IonContent>
          {imageSrc && (
            <Cropper
              src={imageSrc}
              style={{ height: 400, width: '100%' }}
              initialAspectRatio={1}
              guides={false}
              ref={cropperRef}
            />
          )}
          <div className="modal-buttons">
            <IonButton onClick={processImage} disabled={isLoading}>
              {isLoading ? 'Processing...' : 'Analyze Image'}
            </IonButton>
            <IonButton onClick={() => {
              setShowCropper(false);
              setImageSrc(null);
            }} color="danger">
              Cancel
            </IonButton>
          </div>
        </IonContent>
      </IonModal>
    </div>
  );
};

export default SearchWithScan;