import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_MODERN from '@salesforce/resourceUrl/GlobalLogisticsModern';

export default class ModernHeroBanner extends LightningElement {
    heroBgUrl = `${GLOBAL_LOGISTICS_MODERN}/hero-bg.svg`;

    get backgroundStyle() {
        return `background-image: url('${this.heroBgUrl}'); background-size: cover; background-position: center;`;
    }

    handleChatClick() {
        console.log('Chat clicked from hero');
    }
}