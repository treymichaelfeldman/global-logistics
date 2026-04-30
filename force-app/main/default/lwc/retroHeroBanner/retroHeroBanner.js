import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_RETRO from '@salesforce/resourceUrl/GlobalLogisticsRetro';

export default class RetroHeroBanner extends LightningElement {
    underConstructionUrl = `${GLOBAL_LOGISTICS_RETRO}/under-construction.svg`;
    globeUrl = `${GLOBAL_LOGISTICS_RETRO}/globe.svg`;
    
    get backgroundStyle() {
        return `background-image: url('${GLOBAL_LOGISTICS_RETRO}/bg-pattern.svg');`;
    }

    handleCallClick() {
        alert("Please pick up your landline and dial 1-800-GLOBAL-99 !");
    }
}