import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_MODERN from '@salesforce/resourceUrl/GlobalLogisticsModern';

export default class ModernSupportHub extends LightningElement {
    chatIcon = `${GLOBAL_LOGISTICS_MODERN}/icon-chat.svg`;
    supportIcon = `${GLOBAL_LOGISTICS_MODERN}/icon-support.svg`;

    handleChatClick() {
        console.log('Initiating support chat');
    }
}