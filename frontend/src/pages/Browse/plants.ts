import { Plant } from "../../types/plant";

export const plants: Plant[] = [
  {
    id: 1,
    name: "African Copaiba Balsam",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Daniellia oliveri",
    family: "Fabaceae-Caesalpinioideae",
    commonNames: ["African copaiba balsani tree", "West African copal", "Ilorin balsam"],
    localNames: [
      {
        country: "Nigeria",
        names: ["Hausa – Maje", "Igbo – Agba", "Yoruba - Iya"]
      },
      {
        country: "Ghana",
        names: ["Mole - Aonga", "Twi – Osanya", "Konkomba - nialé"]
      }
    ],
    description: "A large savannah and Sudano-Guinean woodland tree that grows on all types of soil. Found from Senegal to Cameroon, Central African Republic, Zaire, Sudan and Angola.",
    uses: {
      general: [
        "Treats headaches and migraines",
        "Used for diarrhea and cough",
        "Treats menstrual pain",
        "Acts as mosquito repellant"
      ],
      specific: [
        {
          region: "Nigeria",
          uses: ["Treats diabetes", "Used for horse skin conditions"]
        }
      ]
    },
    dosage: [
      {
        form: "Decoction",
        instructions: "30g in 900mL water, reduced to 600mL; 1-3 tablespoons daily"
      },
      {
        form: "Infusion",
        instructions: "30g in 600mL water; 3-4 teacups daily"
      }
    ]
  },
  {
    id: 2,
    name: "Desert Date",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Balanites aegyptiaca",
    family: "Zygophyllaceae",
    commonNames: ["Desert date", "Egyptian balsam", "Soap berry tree"],
    localNames: [
      {
        country: "Nigeria",
        names: ["Hausa - Aduwa", "Kanuri - Bito", "Fulfude - Tanni"]
      },
      {
        country: "Sudan",
        names: ["Heglig", "Lalob"]
      }
    ],
    description: "An evergreen tree adapted to Sahel conditions, growing up to 10m tall with strong thorns and yellow-green flowers.",
    uses: {
      general: [
        "Treats liver and spleen problems",
        "Used for stomach pain and jaundice",
        "Anti-diabetic properties",
        "Treats skin diseases"
      ],
      specific: [
        {
          region: "Sudan",
          uses: ["Treatment for asthma", "Used for yellow fever"]
        }
      ]
    },
    dosage: [
      {
        form: "Fruit pulp",
        instructions: "2-3 fruits daily for diabetes management"
      },
      {
        form: "Bark decoction",
        instructions: "15g bark in 500mL water, take twice daily"
      }
    ]
  },
  {
    id: 3,
    name: "African Mahogany",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Khaya senegalensis",
    family: "Meliaceae",
    commonNames: ["African Mahogany", "Senegal Mahogany", "Dry Zone Mahogany"],
    localNames: [
      {
        country: "Nigeria",
        names: ["Hausa - Madachi", "Yoruba - Oganwo", "Fulani - Kahi"]
      }
    ],
    description: "A large deciduous tree reaching 30m in height, known for its valuable timber and medicinal properties.",
    uses: {
      general: [
        "Treats malaria and fever",
        "Used for anemia",
        "Skin infections treatment",
        "Anti-parasitic properties"
      ],
      specific: [
        {
          region: "West Africa",
          uses: ["Treatment for sickle cell anemia", "Used for typhoid fever"]
        }
      ]
    },
    dosage: [
      {
        form: "Bark decoction",
        instructions: "20g bark in 1L water, take one cup thrice daily"
      }
    ]
  },
  {
    id: 4,
    name: "Shea Butter Tree",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Vitellaria paradoxa",
    family: "Sapotaceae",
    commonNames: ["Shea Butter Tree", "Karité Tree"],
    localNames: [
      {
        country: "Nigeria",
        names: ["Hausa - Kadanya", "Fulani - Kareehi", "Yoruba - Emi"]
      },
      {
        country: "Ghana",
        names: ["Dagbani - Nku", "Akan - Nkuto"]
      }
    ],
    description: "A deciduous tree growing up to 15-25m tall, known for its fruit which yields shea butter.",
    uses: {
      general: [
        "Skin moisturizer",
        "Treatment for rheumatism",
        "Anti-inflammatory properties",
        "Wound healing"
      ],
      specific: [
        {
          region: "Mali",
          uses: ["Treatment for nasal congestion", "Used for joint pain"]
        }
      ]
    },
    dosage: [
      {
        form: "Butter application",
        instructions: "Apply directly to affected area twice daily"
      }
    ]
  },
  {
    id: 5,
    name: "African Locust Bean",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Parkia biglobosa",
    family: "Fabaceae",
    commonNames: ["African Locust Bean", "Néré", "Dorowa"],
    localNames: [
      {
        country: "Nigeria",
        names: ["Hausa - Dorowa", "Yoruba - Iru", "Igbo - Ogiri"]
      }
    ],
    description: "A perennial deciduous tree reaching 20m high, valued for its edible seeds and medicinal properties.",
    uses: {
      general: [
        "Treats hypertension",
        "Used for dental problems",
        "Treats eye infections",
        "Anti-parasitic properties"
      ],
      specific: [
        {
          region: "Burkina Faso",
          uses: ["Treatment for bronchitis", "Used for blood pressure"]
        }
      ]
    },
    dosage: [
      {
        form: "Bark infusion",
        instructions: "25g bark in 500mL water, take twice daily"
      }
    ]
  },
  {
    id: 6,
    name: "African Blackwood",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Dalbergia melanoxylon",
    family: "Fabaceae",
    commonNames: ["African Blackwood", "African Ebony", "Grenadillo"],
    localNames: [
      {
        country: "Tanzania",
        names: ["Swahili - Mpingo"]
      },
      {
        country: "Mozambique",
        names: ["Pau Preto"]
      }
    ],
    description: "A slow-growing tree producing one of the most valuable timbers in the world, also used medicinally.",
    uses: {
      general: [
        "Treats abdominal pain",
        "Used for stomach ulcers",
        "Anti-inflammatory properties",
        "Wound healing"
      ],
      specific: [
        {
          region: "Tanzania",
          uses: ["Treatment for scorpion stings", "Used for snake bites"]
        }
      ]
    },
    dosage: [
      {
        form: "Root decoction",
        instructions: "10g root in 500mL water, take once daily"
      }
    ]
  },
  {
    id: 7,
    name: "African Cherry",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Prunus africana",
    family: "Rosaceae",
    commonNames: ["African Cherry", "Red Stinkwood", "African Almond"],
    localNames: [
      {
        country: "Kenya",
        names: ["Kikuyu - Muiri", "Meru - Mweria"]
      }
    ],
    description: "An evergreen tree reaching up to 40m high, known for its medicinal bark used in prostate treatment.",
    uses: {
      general: [
        "Treats prostate problems",
        "Used for kidney disease",
        "Fever reduction",
        "Malaria treatment"
      ],
      specific: [
        {
          region: "Cameroon",
          uses: ["Treatment for urinary problems", "Used for enlarged prostate"]
        }
      ]
    },
    dosage: [
      {
        form: "Bark extract",
        instructions: "100-200mg twice daily after meals"
      }
    ]
  },
  {
    id: 8,
    name: "Moringa",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Moringa oleifera",
    family: "Moringaceae",
    commonNames: ["Drumstick Tree", "Horseradish Tree", "Ben Oil Tree"],
    localNames: [
      {
        country: "Nigeria",
        names: ["Hausa - Zogale", "Yoruba - Ewe Igbale", "Igbo - Odudu"]
      }
    ],
    description: "A fast-growing, drought-resistant tree known as a miracle tree due to its highly nutritious leaves and medicinal properties.",
    uses: {
      general: [
        "Boosts immunity",
        "Treats malnutrition",
        "Anti-inflammatory",
        "Reduces blood sugar"
      ],
      specific: [
        {
          region: "India",
          uses: ["Treatment for arthritis", "Used for anemia"]
        }
      ]
    },
    dosage: [
      {
        form: "Leaf powder",
        instructions: "1-2 teaspoons daily with food"
      },
      {
        form: "Leaf tea",
        instructions: "2g dried leaves in hot water, drink 2-3 times daily"
      }
    ]
  },
  {
    id: 9,
    name: "Devil's Claw",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Harpagophytum procumbens",
    family: "Pedaliaceae",
    commonNames: ["Devil's Claw", "Grapple Plant", "Wood Spider"],
    localNames: [
      {
        country: "Namibia",
        names: ["Otjiherero - Otjihangatene"]
      }
    ],
    description: "A perennial plant with tuberous roots, known for its anti-inflammatory properties.",
    uses: {
      general: [
        "Treats arthritis",
        "Reduces back pain",
        "Anti-inflammatory",
        "Pain relief"
      ],
      specific: [
        {
          region: "South Africa",
          uses: ["Treatment for rheumatism", "Used for tendonitis"]
        }
      ]
    },
    dosage: [
      {
        form: "Root extract",
        instructions: "500mg three times daily with meals"
      }
    ]
  },
  {
    id: 10,
    name: "African Ginger",
    image: "/assets/images/waterCalculator.png",
    botanicalName: "Siphonochilus aethiopicus",
    family: "Zingiberaceae",
    commonNames: ["Wild Ginger", "African Ginger"],
    localNames: [
      {
        country: "South Africa",
        names: ["Zulu - Indungulo", "Xhosa - Isiphephetho"]
      }
    ],
    description: "A perennial herb with aromatic rhizomes, used traditionally for respiratory conditions.",
    uses: {
      general: [
        "Treats coughs",
        "Used for flu symptoms",
        "Anti-asthmatic",
        "Relieves menstrual pain"
      ],
      specific: [
        {
          region: "Zimbabwe",
          uses: ["Treatment for sinusitis", "Used for allergies"]
        }
      ]
    },
    dosage: [
      {
        form: "Rhizome decoction",
        instructions: "5g rhizome in 250mL water, take twice daily"
      },
      {
        form: "Dried powder",
        instructions: "500mg capsules twice daily"
      }
    ]
  }
];