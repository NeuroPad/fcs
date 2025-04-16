import React, { useState } from 'react';
import {
  IonContent,
  IonIcon,
  IonItem,
  IonLabel,
  IonList,
  IonModal,
  IonPage,
  IonCard,
  IonText,
  IonSegment,
  IonSegmentButton,
} from '@ionic/react';
import Header from '../../components/Header/Header';
import { 
  leaf, 
  waterOutline, 
  medkitOutline, 
  flaskOutline,
  alertCircleOutline,
  scaleOutline
} from 'ionicons/icons';
import Container from '../../components/Container/Container';

interface CareTip {
  id: number;
  title: string;
  category: 'Plant Care' | 'Health Tips';
  icon: string;
  shortDescription: string;
  fullDescription: string;
  instructions: string[];
  precautions: string[];
  dosage?: string;
}

const tips: CareTip[] = [
  {
    id: 1,
    title: "Traditional Medicinal Use",
    category: "Health Tips",
    icon: medkitOutline,
    shortDescription: "Treatment for headaches and migraines",
    fullDescription: "The bark and leaves can be used to create traditional remedies for headaches, migraines, and general pain relief.",
    instructions: [
      "Collect fresh leaves or bark from the plant",
      "Clean thoroughly with fresh water",
      "Create a decoction by boiling in water",
      "Let it cool and strain before use",
      "Can be used as a compress or taken orally as prescribed"
    ],
    precautions: [
      "Not suitable for those with heart or kidney conditions",
      "Start with small doses to test tolerance",
      "Discontinue use if any adverse reactions occur"
    ],
    dosage: "Decoction: 30g in 900mL water, reduced to 600mL. Take 1-3 tablespoons daily."
  },
  {
    id: 2,
    title: "Fever and Pain Relief",
    category: "Health Tips",
    icon: flaskOutline,
    shortDescription: "Natural treatment for fever and body pain",
    fullDescription: "Traditional use of leaves in baths for fever reduction and relief from body pain.",
    instructions: [
      "Prepare a bath with warm water",
      "Add prepared leaf infusion to bath water",
      "Soak for 15-20 minutes",
      "Can be used twice daily during fever"
    ],
    precautions: [
      "Test small area of skin first for reactions",
      "Not recommended for high-grade fevers",
      "Consult healthcare provider if fever persists"
    ],
    dosage: "Infusion: 30g in 600mL water for bath addition"
  },
  {
    id: 3,
    title: "Cultivation Care",
    category: "Plant Care",
    icon: leaf,
    shortDescription: "Growing and maintaining healthy plants",
    fullDescription: "Guidelines for proper cultivation in savannah and woodland conditions.",
    instructions: [
      "Plant in well-draining soil",
      "Ensure adequate sunlight exposure",
      "Water moderately during growth season",
      "Maintain spacing for proper growth",
      "Regular pruning for shape control"
    ],
    precautions: [
      "Avoid waterlogged conditions",
      "Protect from extreme temperatures",
      "Monitor for pest infestations"
    ]
  },
  {
    id: 4,
    title: "Harvesting Guidelines",
    category: "Plant Care",
    icon: scaleOutline,
    shortDescription: "Proper harvesting techniques for medicinal use",
    fullDescription: "Best practices for harvesting different plant parts for traditional medicine use.",
    instructions: [
      "Harvest bark during dry season",
      "Collect leaves in early morning",
      "Use clean, sharp tools",
      "Take only what's needed",
      "Store properly in dry conditions"
    ],
    precautions: [
      "Don't over-harvest from one plant",
      "Ensure plant identification is correct",
      "Follow sustainable harvesting practices"
    ]
  },
  {
    id: 5,
    title: "Safety Precautions",
    category: "Health Tips",
    icon: alertCircleOutline,
    shortDescription: "Important safety information for medicinal use",
    fullDescription: "Essential safety guidelines when using the plant for medicinal purposes.",
    instructions: [
      "Verify plant identification before use",
      "Follow recommended dosages strictly",
      "Store preparations properly",
      "Monitor for any adverse reactions",
      "Keep records of usage and effects"
    ],
    precautions: [
      "Not for use during pregnancy",
      "Keep away from children",
      "Avoid mixing with other medications without consultation",
      "Discontinue use if side effects occur"
    ]
  }
];

export default function CareTips() {
  const [showModal, setShowModal] = useState<boolean>(false);
  const [selectedTip, setSelectedTip] = useState<CareTip | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<'Plant Care' | 'Health Tips'>('Health Tips');

  const handleTipClick = (tip: CareTip) => {
    setSelectedTip(tip);
    setShowModal(true);
  };

  const filteredTips = tips.filter(tip => tip.category === selectedCategory);

  return (
    <IonPage>
      <Header title='Care & Health Tips' noBorder />
      <Container padding={false}>
        <IonSegment 
          value={selectedCategory} 
          onIonChange={e => setSelectedCategory(e.detail.value as 'Plant Care' | 'Health Tips')}
        >
          <IonSegmentButton value="Health Tips">
            <IonLabel>Health Tips</IonLabel>
          </IonSegmentButton>
          <IonSegmentButton value="Plant Care">
            <IonLabel>Plant Care</IonLabel>
          </IonSegmentButton>
        </IonSegment>

        <IonList inset={true}>
          {filteredTips.map((tip) => (
            <IonItem 
              key={tip.id} 
              button={true}
              onClick={() => handleTipClick(tip)}
            >
              <IonIcon color='primary' slot='start' icon={tip.icon} />
              <IonLabel>
                <h2>{tip.title}</h2>
                <p>{tip.shortDescription}</p>
              </IonLabel>
            </IonItem>
          ))}
        </IonList>
      </Container>

      <IonModal isOpen={showModal} onDidDismiss={() => setShowModal(false)}>
        {selectedTip && (
          <>
            <Header
              title={selectedTip.title}
              menu={false}
              onClose={() => setShowModal(false)}
            />
            <IonContent className='ion-padding'>
              
                <div className="tip-content">
                  <p className="description">{selectedTip.fullDescription}</p>

                  <div className="section">
                    <h3>Instructions:</h3>
                    <ul>
                      {selectedTip.instructions.map((instruction, index) => (
                        <li key={index}>{instruction}</li>
                      ))}
                    </ul>
                  </div>

                  {selectedTip.dosage && (
                    <div className="section dosage">
                      <h3>Recommended Dosage:</h3>
                      <p>{selectedTip.dosage}</p>
                    </div>
                  )}

                  <div className="section warning">
                    <h3>Precautions:</h3>
                    <ul>
                      {selectedTip.precautions.map((precaution, index) => (
                        <li key={index}>{precaution}</li>
                      ))}
                    </ul>
                  </div>
                </div>
            </IonContent>
          </>
        )}
      </IonModal>
    </IonPage>
  );
}