import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_MODERN from '@salesforce/resourceUrl/GlobalLogisticsModern';

export default class ModernFooter extends LightningElement {
    logoUrl = `${GLOBAL_LOGISTICS_MODERN}/logo.svg`;
    chatIconUrl = `${GLOBAL_LOGISTICS_MODERN}/icon-chat.svg`;

    handleChatClick() {
        console.log('Chat clicked from footer');
    }
}